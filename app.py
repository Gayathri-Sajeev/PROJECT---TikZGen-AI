"""
TikZGen AI — Flask backend
AI-Powered LaTeX Diagram Generator for Academic Research
Uses IBM Watsonx.ai (meta-llama/llama-3-3-70b-instruct) via the chat API.
"""

import os
import re
import io
from pathlib import Path

from flask import Flask, request, jsonify, render_template, send_file
from dotenv import load_dotenv
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

# ── Credentials ───────────────────────────────────────────────────────────────
# Replace your current load_dotenv lines with this:
if (_ENV_PATH := Path(__file__).parent / ".env").exists():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()  # Fallback to standard system environment variables


WATSONX_APIKEY     = os.getenv("WATSONX_APIKEY", "")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_URL        = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

# ── Model ID ──────────────────────────────────────────────────────────────────
MODEL_ID = "meta-llama/llama-3-3-70b-instruct"

# ── Agent instructions (editable) ─────────────────────────────────────────────
AGENT_INSTRUCTIONS = (
    "You are a strict, production-grade LaTeX compiler companion. Your backend engine is "
    "powered exclusively by meta-llama/llama-3-3-70b-instruct through IBM Watsonx.ai. "
    "You must output syntactically perfect, layout-validated LaTeX TikZ code matching "
    "these ironclad instructions:\n\n"

    "1. ABSOLUTE OUTPUT BOUNDARIES: Return ONLY raw LaTeX TikZ code beginning precisely "
    "with \\begin{tikzpicture} and closing with \\end{tikzpicture}. Never include "
    "introductory or concluding conversational dialogue, and never wrap code inside "
    "markdown blocks like ```latex or ```tikz.\n"

    "2. MANDATORY ABSOLUTE COORDINATES: You are strictly forbidden from using relative "
    "positional commands like 'right=of', 'above=of', or 'below left=of' which require "
    "external unconfigured libraries and warp connector vectors. You MUST place every "
    "single node using explicit, absolute numerical X-Y grid coordinates, for example: "
    "at (0,0), at (3.5,0), or at (7,-2).\n"

    "3. MATH PARSING CONSTRAINT: Any inline mathematical symbol or looping evaluation "
    "index calculation inside a coordinate parameter box MUST be fully wrapped in double "
    "curly braces, such as (3, {-\\\\x+1}) or (6, {-\\\\y*1.5}).\n"

    "4. NO LEGACY SYNTAX: Never use the deprecated '\\\\tikzstyle' macro command. You must "
    "define all component dimension constraints, colors, and line profiles using modern "
    "environment bracket header options, like "
    "\\\\begin{tikzpicture}[block/.style={circle, draw}].\n"

    "5. INTUITIVE PIPELINE FLOW: For all sequential processes or flowcharts, design logical "
    "layouts chronologically. Success paths ('Yes') must move straight ahead horizontally "
    "along the positive X-axis line. Rejection lines ('No' loops) must route at clean "
    "90-degree orthogonal paths (-| or |-) back to earlier components, ensuring connection "
    "arrows never strike across text bounding blocks."
)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ── Model — module-level singleton (built once at startup, reused every request)
_model: ModelInference | None = None

def get_model() -> ModelInference:
    """
    Return a cached ModelInference instance.
    Building Credentials + APIClient + ModelInference takes ~1–2 s on every call;
    caching it at module level cuts that overhead to zero after the first request.
    """
    global _model
    if _model is None:
        credentials = Credentials(url=WATSONX_URL, api_key=WATSONX_APIKEY)
        client      = APIClient(credentials=credentials, project_id=WATSONX_PROJECT_ID)
        _model = ModelInference(
            model_id=MODEL_ID,          # "meta-llama/llama-3-3-70b-instruct"
            api_client=client,
            params={
                GenParams.MAX_NEW_TOKENS:     900,   # TikZ diagrams rarely exceed 600 tokens;
                                                     # lower ceiling = faster time-to-last-token
                GenParams.TEMPERATURE:        0.05,  # near-deterministic for code
                GenParams.TOP_P:              0.85,
                GenParams.REPETITION_PENALTY: 1.1,
            },
        )
    return _model


# ── Post-processor: fix the most common model mistakes ───────────────────────
def fix_common_errors(code: str) -> str:
    """
    Apply rule-based corrections for syntax mistakes the model frequently makes.
    Works line-by-line so we don't accidentally corrupt correct code.
    """
    lines = code.split("\n")
    fixed = []

    for line in lines:
        stripped = line.rstrip()

        # Skip blank lines and comments unchanged
        if not stripped or stripped.lstrip().startswith("%"):
            fixed.append(line)
            continue

        # 1. Remove stray \usetikzlibrary / \usepackage / preamble commands
        if re.match(r"\s*\\(usetikzlibrary|usepackage|documentclass|pgfplotsset)\b", stripped):
            # Keep pgfplotsset inside axis environments — it's valid there
            if "pgfplotsset" not in stripped:
                continue  # drop the line entirely

        # 2. Ensure code lines that are not comments and look like statements end with ;
        #    (only if the line contains a TikZ verb and doesn't already end with ; { } or ,)
        tikz_verbs = r"\\(draw|node|path|fill|filldraw|shade|clip|foreach|coordinate|pic)\b"
        if re.search(tikz_verbs, stripped):
            if not re.search(r"[;{},]$", stripped):
                stripped = stripped + ";"
                line = line.rstrip() + ";"

        fixed.append(line)

    return "\n".join(fixed)


# ── Extract the tikzpicture block ─────────────────────────────────────────────
def extract_tikz(raw: str) -> str:
    """
    Strip markdown fences and preamble junk, then extract the tikzpicture block.
    """
    # Strip markdown fences
    raw = re.sub(r"```[a-zA-Z]*\n?", "", raw)
    raw = raw.replace("```", "")

    # Strip preamble commands that must not appear inside tikzpicture
    raw = re.sub(r"\\usetikzlibrary\{[^}]*\}\s*\n?", "", raw)
    raw = re.sub(
        r"\\(documentclass|usepackage|begin\{document\}|end\{document\})[^\n]*\n?",
        "", raw,
    )

    # Extract complete block
    m = re.search(
        r"(\\begin\{tikzpicture\}.*?\\end\{tikzpicture\})",
        raw, flags=re.DOTALL,
    )
    if m:
        return fix_common_errors(m.group(1).strip())

    # Block was cut off — close it
    if r"\begin{tikzpicture}" in raw:
        snippet = raw[raw.index(r"\begin{tikzpicture}"):].strip()
        return fix_common_errors(snippet + "\n\\end{tikzpicture}")

    return fix_common_errors(raw.strip())


# ── Prompt builder ────────────────────────────────────────────────────────────
def call_model(system: str, user: str) -> str:
    """
    Use the chat (messages) API so the model receives properly structured
    system/user turns — much more reliable than raw token strings.
    """
    model = get_model()

    # ibm-watsonx-ai >= 1.1 exposes chat() on ModelInference
    try:
        response = model.chat(messages=[
            {"role": "system",  "content": system},
            {"role": "user",    "content": user},
        ])
        # Response shape: {"choices": [{"message": {"content": "..."}}]}
        return response["choices"][0]["message"]["content"].strip()
    except (AttributeError, KeyError, TypeError):
        # Fallback: raw generate_text with explicit Llama-3 tokens
        prompt = (
            f"<|begin_of_text|>"
            f"<|start_header_id|>system<|end_header_id|>\n{system}<|eot_id|>"
            f"<|start_header_id|>user<|end_header_id|>\n{user}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n"
        )
        return model.generate_text(prompt=prompt).strip()


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """
    POST JSON: { description, existing_code?, refinement? }
    Returns:   { tikz_code } or { error }
    """
    try:
        data          = request.get_json(force=True) or {}
        description   = data.get("description",   "").strip()
        existing_code = data.get("existing_code", "").strip()
        refinement    = data.get("refinement",    "").strip()

        if not description and not refinement:
            return jsonify({"error": "Please enter a description or refinement prompt."}), 400

        if not WATSONX_APIKEY or not WATSONX_PROJECT_ID:
            return jsonify({"error": "Watsonx credentials not configured in .env file."}), 500

        # Build user message
        if refinement and existing_code:
            user_msg = (
                f"Here is the current TikZ diagram:\n\n"
                f"{existing_code}\n\n"
                f"Apply ONLY this change and return the complete updated diagram "
                f"(full \\begin{{tikzpicture}}...\\end{{tikzpicture}} block):\n"
                f"{refinement}"
            )
        else:
            user_msg = (
                f"Generate a TikZ diagram for:\n{description}\n\n"
                f"Return the complete \\begin{{tikzpicture}}...\\end{{tikzpicture}} block only."
            )

        raw       = call_model(AGENT_INSTRUCTIONS, user_msg)
        tikz_code = extract_tikz(raw)
        return jsonify({"tikz_code": tikz_code})

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Generation failed: {exc}"}), 500


@app.route("/download", methods=["POST"])
def download():
    """Return the TikZ code as a complete compilable standalone .tex file."""
    data      = request.get_json(force=True) or {}
    tikz_code = data.get("tikz_code", "")

    latex_doc = (
        "\\documentclass[tikz,border=10pt]{standalone}\n"
        "\\usepackage{tikz}\n"
        "\\usepackage{pgfplots}\n"
        "\\usetikzlibrary{"
            "arrows.meta,shapes.geometric,shapes.symbols,"
            "positioning,calc,fit,"
            "decorations.pathmorphing,decorations.markings,"
            "matrix,chains"
        "}\n"
        "\\pgfplotsset{compat=1.18}\n"
        "\\begin{document}\n"
        f"{tikz_code}\n"
        "\\end{document}\n"
    )

    buf = io.BytesIO(latex_doc.encode("utf-8"))
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/x-tex",
        as_attachment=True,
        download_name="tikzgen_diagram.tex",
    )


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/healthz")
def healthz():
    def mask(v: str) -> str:
        if not v or v.startswith("your_"):
            return "⚠ NOT SET (placeholder)"
        if len(v) <= 10:
            return "⚠ TOO SHORT"
        return f"{v[:6]}…{v[-4:]}"

    return jsonify({
        "model_id":           MODEL_ID,
        "env_file_found":     _ENV_PATH.exists(),
        "WATSONX_APIKEY":     mask(WATSONX_APIKEY),
        "WATSONX_PROJECT_ID": mask(WATSONX_PROJECT_ID),
        "WATSONX_URL":        WATSONX_URL or "⚠ NOT SET",
        "status": (
            "OK"
            if WATSONX_APIKEY and not WATSONX_APIKEY.startswith("your_")
               and WATSONX_PROJECT_ID and not WATSONX_PROJECT_ID.startswith("your_")
            else "ERROR — credentials missing"
        ),
    })


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

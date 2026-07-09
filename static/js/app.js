/**
 * TikZGen AI — Frontend Controller
 * Handles: text input, generation, iterative refinement,
 *          copy-to-clipboard, .tex download, and TikZ syntax highlighting.
 */

(() => {
  "use strict";

  // ── Element refs ────────────────────────────────────────────────────────────
  const descriptionInput = document.getElementById("descriptionInput");
  const generateBtn      = document.getElementById("generateBtn");
  const generateLabel    = document.getElementById("generateLabel");
  const generateSpinner  = document.getElementById("generateSpinner");
  const refinementInput  = document.getElementById("refinementInput");
  const refineBtn        = document.getElementById("refineBtn");
  const statusMsg        = document.getElementById("statusMsg");
  const emptyState       = document.getElementById("emptyState");
  const codeBlock        = document.getElementById("codeBlock");
  const codeContent      = document.getElementById("codeContent");
  const copyBtn          = document.getElementById("copyBtn");
  const downloadBtn      = document.getElementById("downloadBtn");
  const lineCount        = document.getElementById("lineCount");

  // ── State ────────────────────────────────────────────────────────────────────
  let currentTikzCode = "";

  // ── Helpers ──────────────────────────────────────────────────────────────────
  function setLoading(active) {
    generateBtn.disabled = active;
    refineBtn.disabled   = active;
    generateLabel.classList.toggle("d-none", active);
    generateSpinner.classList.toggle("d-none", !active);
  }

  function showStatus(message, type = "error") {
    statusMsg.textContent = message;
    statusMsg.className   = `status-msg ${type}`;
    statusMsg.classList.remove("d-none");
  }

  function clearStatus() {
    statusMsg.classList.add("d-none");
    statusMsg.textContent = "";
  }

  // ── TikZ syntax highlighter ──────────────────────────────────────────────────
  function highlightTikz(raw) {
    // Escape HTML entities first
    let s = raw
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Comments  % …  (must come before command highlighting)
    s = s.replace(/(%.*)$/gm, '<span class="cmt">$1</span>');

    // LaTeX keywords vs generic commands
    s = s.replace(/\\([a-zA-Z@]+)/g, (m, cmd) => {
      const kws = [
        "begin", "end", "node", "draw", "fill", "path", "foreach",
        "coordinate", "clip", "scope", "tikzset", "usetikzlibrary",
        "pgfplotsset", "addplot", "axis",
      ];
      return kws.includes(cmd)
        ? `<span class="kw">\\${cmd}</span>`
        : `<span class="cmd">\\${cmd}</span>`;
    });

    // Options in square brackets  [...]
    s = s.replace(/(\[[^\]]*\])/g, '<span class="opt">$1</span>');

    return s;
  }

  function renderCode(tikz) {
    currentTikzCode       = tikz;
    codeContent.innerHTML = highlightTikz(tikz);
    codeBlock.classList.remove("d-none");
    emptyState.classList.add("d-none");

    const lines = tikz.split("\n").length;
    lineCount.textContent = `${lines} lines`;
    lineCount.classList.remove("d-none");

    copyBtn.disabled     = false;
    downloadBtn.disabled = false;
  }

  // ── Core request ─────────────────────────────────────────────────────────────
  async function sendRequest(isRefinement) {
    clearStatus();

    const description = descriptionInput.value.trim();
    const refinement  = refinementInput.value.trim();

    // Validation
    if (isRefinement) {
      if (!refinement) {
        showStatus("Please enter a refinement prompt.", "error");
        return;
      }
      if (!currentTikzCode) {
        showStatus("Generate a diagram first before refining.", "error");
        return;
      }
    } else {
      if (!description) {
        showStatus("Please enter a description before generating.", "error");
        return;
      }
    }

    setLoading(true);

    try {
      const payload = isRefinement
        ? { description: "", existing_code: currentTikzCode, refinement }
        : { description, existing_code: "", refinement: "" };

      const response = await fetch("/generate", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(data.error || `Server error ${response.status}`);
      }

      renderCode(data.tikz_code);
      showStatus("Diagram generated successfully.", "success");

      if (isRefinement) refinementInput.value = "";

    } catch (err) {
      showStatus(`Error: ${err.message}`, "error");
    } finally {
      setLoading(false);
    }
  }

  // ── Event bindings ────────────────────────────────────────────────────────────
  generateBtn.addEventListener("click", () => sendRequest(false));
  refineBtn.addEventListener("click",   () => sendRequest(true));

  refinementInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendRequest(true);
    }
  });

  // ── Copy ─────────────────────────────────────────────────────────────────────
  copyBtn.addEventListener("click", () => {
    if (!currentTikzCode) return;

    // Primary: modern Clipboard API (requires HTTPS or localhost)
    // Fallback: execCommand via a temporary off-screen textarea (works on all origins)
    const doFlash = () => {
      const original = copyBtn.innerHTML;
      copyBtn.innerHTML   = '<i class="bi bi-check2 me-1"></i>Copied!';
      copyBtn.style.color = "#3fb950";
      setTimeout(() => {
        copyBtn.innerHTML   = original;
        copyBtn.style.color = "";
      }, 2000);
    };

    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(currentTikzCode)
        .then(doFlash)
        .catch(() => fallbackCopy());
    } else {
      fallbackCopy();
    }

    function fallbackCopy() {
      const ta = document.createElement("textarea");
      ta.value = currentTikzCode;
      // Position off-screen so it doesn't cause a visible jump
      ta.style.cssText = "position:fixed;top:-9999px;left:-9999px;opacity:0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try {
        document.execCommand("copy");
        doFlash();
      } catch {
        showStatus("Copy failed — please select the code and press Ctrl+C.", "error");
      } finally {
        document.body.removeChild(ta);
      }
    }
  });

  // ── Download ─────────────────────────────────────────────────────────────────
  downloadBtn.addEventListener("click", async () => {
    if (!currentTikzCode) return;
    try {
      const response = await fetch("/download", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ tikz_code: currentTikzCode }),
      });
      if (!response.ok) throw new Error("Download failed");
      const blob = await response.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = "tikzgen_diagram.tex";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      showStatus(`Download error: ${err.message}`, "error");
    }
  });

})();

# PROJECT---TikZGen-AI
LaTeX Diagram Generator 

Production-Grade LaTeX Diagram Generator for Academic ResearchTikZGen AI is an intelligent, agentic development system engineered to automate the generation of publication-ready vector graphics for scientific documents. This platform translates advanced natural language specifications directly into flawless, syntactically perfect LaTeX TikZ code.By running on IBM Cloud Pak for Data and leveraging high-capacity LLM infrastructures, TikZGen AI bridges the gap between conversational research conceptualization and complex geometric canvas programming, completely eliminating manual syntax debugging and compile errors for researchers.


Key Technical Features
1.Prompt-Driven Interface: Ingests multi-turn conversational descriptions to generate intricate structural and mathematical diagrams instantly.
2.Agentic Constraint Enforcement: Incorporates a rigid server-side instruction layer (AGENT_INSTRUCTIONS) to guarantee absolute coordinate grid mapping, modern property handlers, and loop boundary conditions.
3.Iterative Refinement Engine: Fully supports modification prompts (e.g., "make connections blue", "increase node spacing") to dynamically update existing code without resetting state.
4.Zero-Overhead Export Utilities: Equips researchers with direct "Copy to Clipboard" and instant standalone .tex file downloading modules.Premium Responsive Dashboard: Features a high-utility, desktop-optimized dark-mode interface styled cleanly with Bootstrap.


 Technology StackEnterprise AI Infrastructure: 
*IBM watsonx.ai Studio (via Cloud Pak for Data as a Service).
*Core Inference Model: meta-llama/llama-3-3-70b-instruct (Configured with Greedy Decoding and optimized token thresholds for high-fidelity code synthesis).
*Application Controller: Python 3.11+ / Flask Framework.
*Integration Software: ibm-watsonx-ai Official Software Development Kit (SDK).
*UI Delivery: HTML5, CSS3, JavaScript, Bootstrap 5.

Workspace Configuration
1. Requirements Installation
   Install the necessary application runtimes and integration dependencies locally:pip install flask ibm-watsonx-ai python-dotenv
2. Environment Setup (.env)
   Create a local .env file inside the project root workspace directory to securely bind your platform credentials:WATSONX_APIKEY="your_ibm_cloud_iam_api_key"WATSONX_PROJECT_ID="your_watsonx_studio_project_guid"WATSONX_URL="https://ibm.com"
3. Application Execution
   Boot the local server gateway:python app.py

Open your browser framework and target: http://localhost:5000

Repository File Index
#app.py: Core Flask Server & watsonx.ai 
#SDK Controller.env: Local Credentials Store (Ignored by Git)
#requirements.txt: Software Runtime Dependency Manifest
#templates/index.html: Premium Dark-Mode User Dashboard

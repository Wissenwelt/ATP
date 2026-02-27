# Agent Tool Protocol (ATP) 🔌

**The Universal "USB-C" Layer for the Agentic Web.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![VS Code Provider](https://img.shields.io/badge/vscode-extension-purple)]()

## 🎯 The Mission
As the Agentic Web rapidly scales, multi-agent framework integration remains fundamentally broken and fragmented.
*   **Siloed Tools:** An amazing Model Context Protocol (MCP) server written for Google Drive doesn't play natively in **CrewAI**, **LangChain**, or **AutoGen** without hundreds of lines of brittle, manual wrapper code.
*   **Model "Hallucinations":** Without safety protocols, LLM agents often construct invalid JSON payloads attempting to interact with tools resulting in system crashes.
*   **Zero Observability:** When debugging a multi-agent orchestrated run across networks, tracking the specific data a specific agent sent to a specific microservice tool is nearly impossible.

**We are solving the "Integration Tax".** 

ATP acts as a unified Middleware Protocol and Databased Registry sitting perfectly between any AI Model ("The Brain") and any MCP Server ("The Hands"). 
By routing requests through ATP, we completely automate the semantic type translation, safety validation, and visual execution observability of tool usage across *all* multi-agent frameworks instantly.

## 🚀 Why This Project is Important
Other groups are focused on building single-use tools. **We are focused on building the universal dictionary that allows *all* tools to talk to *all* agents natively.** 

As Enterprise organizations prepare to onboard thousands of specialized, customized AI agents, those agents will require reliable, secure, and cross-framework highways to interact with their corporate tool fleets. By providing this decoupled translation and observability layer, ATP ensures enterprises can instantly swap out underlying agent reasoning configurations without touching a single line of their custom tool integrations.

---

## 🏗️ Core Components
The core ATP ecosystem consists of three interconnected layers:
1.  **ATP Bridge (`atp_translator.py`)**: A Python SDK leveraging `pydantic` and `ast` layer manipulation that connects to remote MCP servers and dynamically yields fully typed, Framework-native execution classes (e.g., dynamically subclassing `autogen_core.tools.BaseTool`).
2.  **ATP Registry (`db.py` & `api.py`)**: A "Gold Standard" SQLite database registry that catalogs "Manifest Hashes" of verified tool schemas and exposes a historical telemetry backbone API.
3.  **ATP Guardian (`/atp-guardian`)**: A beautifully engineered, native TypeScript VS Code extension and dashboard. Guardian silently poles our backend API to visually highlight exact tool executions, arguments, returns, and payload anomalies within your local IDE workspace.

---

## 🚦 Current Status
ATP has successfully proven out its core architectural objectives!
*   **✅ Phase 1 (The Translator):** Complete. Achieved direct mapping of foreign MCP server schemas into highly-compatible execution classes.
*   **✅ Phase 2 (The Registry):** Complete. Automated SQLite persistence layer storing exact payload structures of discovered tools via Manifest Hashing.
*   **✅ Phase 3 (The Guardian):** Complete. Launched our live React Webview inside VS Code that continually monitors backend API telemetry endpoints automatically triggered by agents.
*   **✅ Phase 4 (The Protocol):** Complete. Achieved full Universal Framework Support. Our `httpx` telemetry and wrapper functions transparently translate tools for **CrewAI**, **LangChain**, and **AutoGen v0.4** completely flawlessly.

### 🛠️ Enterprise Architecture & Best Practices Roadmap
We need to harden the protocol for scalable enterprise systems. Future updates will implement the **"Bring Your Own Database" (BYOD) Open-Source Model** (similar to Apache Airflow), decoupling our core Engine from the Storage layer.

#### 1. Database Connection Management (FastAPI Best Practice)
*   **Current State:** The system uses a globally instantiated `SessionLocal` object in `db.py` to handle database operations. Under massive concurrent multi-agent workloads, global sessions can lead to thread-safety issues and database file locks.
*   **Future Implementation:** We will refactor `api.py` to implement **FastAPI Dependency Injection** (using `Depends(get_db)` generators). This architectural best practice guarantees that a fresh, isolated database connection is initialized for every single API request, and effectively guarantees the connection is safely closed when the request yields.

#### 2. The BYOD Open-Source Data Plane (Phase 5)
*   **Current State:** SQLite fallback databases are hardcoded locally.
*   **Future Implementation:** ATP will intelligently query OS-level environment variables (e.g., `ATP_DATABASE_URL`). 
    *   **Local Developers:** If unconfigured, the system retains its perfect zero-config quickstart using `sqlite:///atp_registry.db`.
    *   **Enterprise Teams:** Businesses can point the variable to their internal corporate `postgresql://` RDS/Azure instances. ATP will dynamically build a high-concurrency SQLAlchemy engine, meaning the execution logs never touch our servers, ensuring total open-source business autonomy and privacy.

#### 3. Behavioral Guardrails (Phase 6)
*   Capturing historical anomaly telemetry via the Guardian system and injecting auto-generated instructions into subsequent system prompts, preventing an agent from committing the same logical parsing mistake twice on a specific tool.

---

## 🤝 Fork, Replicate & Contribute!
If you are passionate about standardizing the Agentic Web, **we want your help!** Please consider exploring the source code or contributing to our next phase.

If you find this project interesting, please give us a **Star ⭐** and **Fork** this repo to try it out yourself!

### Prerequisites
*   Python 3.10+
*   Node.js 18+ & npm
*   VS Code

### 1. Backend Protocol Setup
Clone the repository, initialize your virtual environment, and construct your core dependencies:

```bash
git clone https://github.com/organization/ATP_Protocol.git
cd ATP_Protocol

# Initialize and map virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install requirements mapping (MCP, CrewAI, AutoGen-Ext, Langchain, FastAPI)
pip install -r requirements.txt
```

### 2. Stand Up the ATP Observability Pipeline
This command initializes our internal SQLite persistence layers on port 8000 and awaits asynchronous agent execution posts.
```bash
python -m uvicorn api:app --reload --port 8000
```
> *Leave this Uvicorn process running in an active shell.*

### 3. Spin Up the Guardian VS Code Observer
Open a new shell instance to compile and launch the VS Code Extension.
```bash
cd atp-guardian
npm install
npm run compile
```
*   Launch a new VS Code Window pointing to the `/atp-guardian` directory.
*   Hit **`F5`** to fire up the Extension Development Host.
*   Inside the new host IDE window, open the Command Palette (`Ctrl+Shift+P` OR `Cmd+Shift+P`).
*   Select the **`ATP Guardian: Open Monitor`** package directive. The UI panel will now spawn and begin listening.

### 4. Execute a Multi-Agent Test Framework
Now that the server is listening and the Guardian panel is monitoring, jump back to your original IDE network and execute one of our multi-agent test frameworks. Provide OpenAI or Gemini Keys if testing full LLM chat completion flows!

```bash
# Test Framework A: Langchain + CrewAI execution pathways
python test_atp.py

# Test Framework B: AutoGen 0.4 API executions
# Ensure API keys are exported: export GEMINI_API_KEY="your-api-key"
python test_autogen_atp.py
```

> **Watch the Guardian Webview!** As you run these framework instances, the tool invocations will instantly populate across the monitoring system displaying Framework provenance, Tool Names, Parameter definitions, and Return anomalies dynamically.

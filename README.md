<p align="center">
  <img src="logo.png" width="140" alt="SkillWise Logo"/>
</p>

<h1 align="center">
  🧠 SkillWise
</h1>

<p align="center">
  <b>AI-Powered Career Ingestion Engine & 6-Month Hyper-Personalized Learning Path Generator</b>
</p>

<p align="center">
  <a href="https://skillwise-sahaj33.streamlit.app/" target="_blank">
    <img src="https://img.shields.io/badge/Deployed%20on-Streamlit-ff4b4b?style=flat-square&logo=streamlit" alt="Streamlit Deploy">
  </a>
  &nbsp;
  <a href="https://github.com/sizwinz/SkillWise/stargazers">
    <img src="https://img.shields.io/github/stars/sizwinz/SkillWise?style=flat-square&logo=github" alt="GitHub Stars">
  </a>
  &nbsp;
  <a href="https://github.com/sizwinz/SkillWise/network/members">
    <img src="https://img.shields.io/github/forks/sizwinz/SkillWise?style=flat-square&logo=github" alt="GitHub Forks">
  </a>
  &nbsp;
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="MIT License">
  </a>
</p>

<p align="center">
  <a href="#-core-features">Features</a> •
  <a href="#%EF%B8%8F-architecture--stack">Architecture</a> •
  <a href="#-installation--setup">Setup</a> •
  <a href="#%EF%B8%8F-configuration">Configuration</a> •
  <a href="#-directory-structure">Structure</a> •
  <a href="#-license">License</a>
</p>

---

SkillWise changes how developers and tech professionals approach career transitions. By passing engineering resumes or structured LinkedIn datasets through state-of-the-art LLMs, SkillWise performs programmatic gap detection, runs zero-shot job simulation matching, visualizes progress timelines dynamically, and tracks target-milestone completion natively—locally backed by deterministic persistence.

---

## 🚀 Core Features

### 1. Multi-Format Resume Ingestion Engine
* **Native Parsing:** Programmatic text layer stripping from standard format PDFs via PyMuPDF (`fitz`).
* **OCR Fallback Subsystem:** Automatic fallback execution via `pytesseract` to handle image-only, scanned resumes at high-DPI configuration if initial text yield fails validation filters.
* **LinkedIn Data Ingestion:** Explicit dictionary mapping and traversal routines parsing comprehensive LinkedIn profile JSON data exports (including experience schemas, timeframes, and certifications).

### 2. Deep Skill Gap Matrix & Analysis
* **Contextual Goal Extraction:** Zero-shot analysis of high-level targeting statements (e.g., "AI Developer") utilizing Gemini to extract hard/soft skill requirements instantly.
* **Narrative Gap Assessment:** Avoids simple keyword-matching failure-modes. Runs comparative analysis against an ideal candidate profile to point out abstract missing components (e.g., architectural experiences, specific design patterns, system-level exposures).

### 3. Interactive Roadmap Orchestration
* **Dynamic Gantt Visualizations:** Translates markdown-based temporal learning schedules directly into interactive, color-coded timelines rendered natively via Plotly Express charts.
* **Integrated Checklist & State Syncer:** Deep tracking logic parsing granular task listings out of roadmap variants to map completion flags into sync routines.

### 4. Job Role Simulation Environment
* **Ad-Hoc JD Matching:** Subsystem enabling immediate resume pairing against arbitrary copy-pasted job descriptions to produce clear fit metrics and percentage compatibility ratings.
* **Targeted Remediation Plans:** Overrides basic roadmaps to generate targeted, hyper-focused 6-month plans entirely designed around neutralizing deficiencies found in a given job description.

### 5. Persistent Session Management & State Storage
* **Local DB State Layer:** Lightweight filesystem tracking layer using predictable SHA-256 hashes computed over a user's resume, goal, and role variations to auto-reconcile state indices.
* **Sidebar History Workspace:** Context management dashboard allowing deep searching, active roadmap pinning (`Set Active`), explicit JSON data drops, continuation loading, and safe deletion states.

---

## 🛠️ Architecture & Stack

SkillWise uses an asynchronous, modular design segregating front-end client rendering states from model interface layers and systemic document tools:


```mermaid
graph TD
    %% Nodes
    UI["Streamlit UI<br>(app.py)"]
    Parser["Resume Parser<br>(resume_parser.py)"]
    LLM["LLM Execution<br>Pipelines"]
    DB["Persistence Layer<br>(roadmaps_db.json)"]
    
    PyMuPDF["PyMuPDF<br>(Text)"]
    GeminiFlash["gemini-2.0-flash<br>(Goal & JD Analysis)"]
    GeminiLite["gemini-2.5-flash-lite<br>(Roadmap & Gaps)"]

    %% Connections
    UI --> Parser
    UI --> LLM
    UI --> DB

    Parser --> PyMuPDF
    LLM --> GeminiFlash
    LLM --> GeminiLite

    %% Styling (Optional)
    style UI fill:#2c3e50,stroke:#34495e,stroke-width:2px,color:#fff
    style LLM fill:#16a085,stroke:#1abc9c,stroke-width:2px,color:#fff
    style Parser fill:#2980b9,stroke:#3498db,stroke-width:2px,color:#fff
    style DB fill:#7f8c8d,stroke:#95a5a6,stroke-width:2px,color:#fff

```

* **Frontend Framework:** Streamlit (Layout engine, Session state controller).
* **AI Core Orchestration Platform:** `google-generativeai` utilizing specific model targeting blocks:
  * `gemini-2.0-flash` for high-speed analysis tasks (Career Goal Breakdown & Job Fit Simulator scoring).
  * `gemini-2.5-flash-lite` for token-heavy analytical generations (Roadmap Synthesis & Smart Gap generation).
  * `gemini-1.5-flash` for ad-hoc user question answering over cached data blocks.
* **Visualization Layer:** Plotly Express + Pandas (Time-delta processing engines tracking duration descriptors).
* **Document Exporters:** ReportLab Custom Canvas Engine (Standardized ASCII conversion matrices compiling text metrics safely into layout grids while injecting raw analysis summaries into output objects).

---

## 💻 Installation & Setup

### Prerequisites
* **Python 3.11** or **Python 3.13**
* **Tesseract OCR Engine** binaries configured in the execution environment system path.

### 1. Clone the Repository
```bash
git clone [https://github.com/sizwinz/SkillWise.git](https://github.com/sizwinz/SkillWise.git)
cd SkillWise

```

### 2. Install System Dependencies (Required for Scanned PDF Handling)

* **Debian/Ubuntu Linux:**
```bash
sudo apt update
sudo apt install -y tesseract-ocr

```


* **macOS (via Homebrew):**
```bash
brew install tesseract

```


* **Windows:**
Download and run the windows executable distribution installer from the official [UB-Mannheim Tesseract Repository](https://github.com/UB-Mannheim/tesseract/wiki). Ensure the binary path is correctly included inside your Environment variables `PATH`.

### 3. Install Python Package Dependencies

```bash
pip install -r requirements.txt

```

---

## ⚙️ Configuration

Set up configuration settings by creating a `.env` environment variables block inside your directory root path:

```env
GEMINI_API_KEY=your_actual_google_gemini_api_key_here

```

*Alternatively, the application sidebar provides a secure password-masked configuration utility textbox allowing direct manual entry of your `GEMINI_API_KEY` straight into the context lifecycle cache at runtime.*

### Launching the Application

Execute the application lifecycle tracking loop locally using the main package reference file:

```bash
streamlit run app.py

```

---

## 📂 Directory Structure

```shadow
SkillWise/
├── .devcontainer/
│   └── devcontainer.json    # Standard container-orchestrated runtime definitions
├── screenshots/
│   ├── upload.png           # User onboarding / application capture panels
│   └── roadmap.png          # Visual interactive dashboard timelines
├── app.py                   # Central Streamlit entrypoint & component pipeline
├── resume_parser.py         # Fitz extraction logic & Tesseract scanning engines
├── goal_analyzer.py         # Target role & token parsing validation modules
├── roadmap_generator.py     # Retry-backoff logic calling Gemini generation routines
├── smart_gap_analyzer.py    # Zero-shot resume deficiency scoring pipelines
├── skills_data.json         # Fallback taxonomy lists tracking static tech skills
├── roadmaps_db.json         # Local encrypted persistence history layer
├── style.css                # Custom UI styling configurations
├── requirements.txt         # Primary pinned setup package dependency lists
└── packages.txt             # Mandatory platform-layer binary installation targets

```

---

## 📜 License

Distributed directly under the terms of the open-source **MIT License**. Check out the [`LICENSE`](https://www.google.com/search?q=LICENSE) verification file for detailed phrasing constraints.

---

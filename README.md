# Sulfur

A local-first AI coding assistant desktop app that connects to locally-running LLMs. Chat with an AI that can read, write, edit, and search files in your workspace — all running entirely on your machine.

## Features

- **100% Local** — No cloud, no telemetry, no data leaves your machine
- **Multi-Backend** — llama.cpp (bundled), LM Studio, or Ollama
- **Tool Calling** — AI can read, write, edit, and search your files with permission controls
- **Streaming Responses** — Real-time streaming chat with smooth rendering
- **Session Management** — Create, switch, rename, and delete chat sessions
- **Workspace Attachments** — Attach files and folders for the AI to work with
- **11 Color Themes** — Sulfur, Daylight, Void, Aqua, Cherry, Forest, Fire, Nebula, Slate, Amber, Emerald
- **Frameless Window** — Custom title bar with drag, resize, and minimize
- **PDF Parsing** — Ingest and analyze PDF documents

## Prerequisites

- **Windows** (the app ships Windows binaries)
- **Python 3.11+** (3.12 recommended)
- **NVIDIA GPU** with CUDA drivers (for GPU acceleration)
- **GGUF model files** placed in the `models/` directory

## Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/sulfur.git
cd sulfur

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Place your GGUF model(s) in the models/ folder

# Run the app
python brain.py
```

Or simply double-click `run_ui.bat`.

## Configuration

All settings are stored in `preferences.json` and can be adjusted from the in-app Settings dialog:

| Setting | Description |
|---------|-------------|
| `BACKEND_TYPE` | `llama_cpp`, `lm_studio`, or `ollama` |
| `NUM_CTX` | Context window size |
| `TEMPERATURE` | Response randomness (0.0–2.0) |
| `GPU_LAYERS` | Layers offloaded to GPU (`-1` = all) |
| `ALLOW_FILE_EDITS` | Enable/disable file editing |
| `AUTO_APPLY_EDITS` | Auto-apply edits without confirmation |

## Project Structure

```
├── brain.py              # Entry point
├── run_ui.bat            # Windows launcher
├── requirements.txt      # Python dependencies
├── src/modules/          # Core logic (backends, inference, sessions, tools)
├── ui/                   # PyQt6 GUI (chat, sidebar, settings, title bar)
├── bin/llama-cpp-cuda/   # Bundled llama.cpp binaries
├── models/               # GGUF model files (gitignored)
├── instructions/         # System prompt templates
└── sessions/             # Per-session chat history (gitignored)
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12+ |
| GUI | PyQt6 |
| Inference | llama.cpp / LM Studio / Ollama |
| Doc Parsing | PyMuPDF |


## Acknowledgements

- [llama.cpp](https://github.com/ggerganov/llama.cpp) for local LLM inference
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI framework
- [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF parsing

# Contributing to Sulfur

Thanks for your interest in contributing! This document outlines the process for contributing to the project.

## Getting Started

### Development Setup

1. Fork the repository and clone it locally
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Place a GGUF model in the `models/` directory (or configure an external backend)
4. Run the app to verify everything works: `python brain.py`

### Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code
- Use descriptive variable and function names
- Keep functions focused and reasonably sized
- Use type hints where practical
- Prefer existing patterns look at neighboring files before introducing new conventions

### Project Architecture

| Directory | Purpose |
|-----------|---------|
| `src/modules/backend/` | Pluggable LLM backend abstraction (base class + implementations) |
| `src/modules/more_modules/` | Core streaming pipeline, tool execution, memory ops |
| `src/modules/` | Config, preferences, sessions, file operations, document parsing |
| `ui/` | All PyQt6 GUI components |

- `brain.py` is the entry point it creates the QApplication and main window
- `ui/app.py` (`App` class) orchestrates the UI and streaming pipeline
- `src/modules/backend/__init__.py` acts as a backend factory
- `src/modules/more_modules/chat_stream.py` handles the core streaming + tool-calling loop

### Adding a New Backend

1. Create a new file in `src/modules/backend/` (e.g., `my_backend.py`)
2. Subclass `BaseBackend` from `base.py`
3. Implement the required abstract methods (`start`, `shutdown`, `chat_completion`, `get_models`, etc.)
4. Register it in `src/modules/backend/__init__.py` in the `create_backend` factory

### Adding a New Theme

Add a new palette entry to the `PALETTES` dictionary in `src/modules/configurations.py`, following the existing pattern.

## Pull Request Process

1. Create a feature branch from `main` with a descriptive name (e.g., `feat/add-dark-mode`, `fix/model-loading-error`)
2. Make your changes, ensuring the app runs without errors
3. Test with at least one backend (llama.cpp, LM Studio, or Ollama)
4. Submit a pull request with a clear description of what changed and why
5. Reference any related issues

## Reporting Bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) when filing issues. Include:
- Your environment (Windows version, Python version, GPU)
- Steps to reproduce
- Expected vs. actual behavior
- Relevant logs from `llama_server.log` if applicable

# Sulfur v1.0.0

A portable AI coding assistant that runs on your PC. No internet needed.

---

## How to get started (3 steps)

### Step 1: Get a model

Sulfur needs a GGUF model file to work. Download one from Hugging Face:

- [Qwen 2.5 Coder 7B](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF) (good for coding, ~4 GB)
- [Gemma 3 4B](https://huggingface.co/google/gemma-3-4b-it-GGUF) (lighter, ~3 GB)

Place the `.gguf` file anywhere on your PC. You will point Sulfur to it later.

> **Tip:** If you already use LM Studio or Ollama, skip this step. Sulfur can connect to those too.

### Step 2: Set up llama.cpp (optional)

If you are using the built-in llama.cpp backend, you need the binaries:

1. Download from [llama.cpp releases](https://github.com/ggerganov/llama.cpp/releases) (pick the latest `win-x64-cuda` zip)
2. Extract everything into the `bin/llama-cpp-cuda/` folder next to `Sulfur.exe`

> Already done in this zip? You are good to go.

### Step 3: Launch and configure

1. Double-click **Sulfur.exe**
2. Click the gear icon (top right) to open **Settings**
3. Go to the **Model** tab:
   - Set **Backend** to `llama_cpp` (or `LM Studio` / `Ollama` if you use those)
   - Click **Browse** next to "GGUF Folder" and select the folder with your `.gguf` files
   - Pick a model from the dropdown
4. Click **Save** at the bottom

That's it. Start typing in the chat bar.

---

## Basic usage

| Action | How |
|--------|-----|
| Chat with AI | Type in the bottom bar, hit Enter |
| Attach files | Click "Attach File" or "Attach Folder" to let the AI read your code |
| Let AI edit files | The AI can write and edit files in your workspace (enable in Settings) |
| Switch sessions | Use the sidebar on the left to create/switch chat sessions |
| Change theme | Settings → General → Palette |
| Tune performance | Settings → Advanced → adjust context size, threads, GPU layers |

---

## Requirements

- Windows 10 or 11
- For llama.cpp: NVIDIA GPU with CUDA drivers
- For LM Studio / Ollama: any GPU works, including AMD and Intel

---

## Files in this zip

```
Sulfur/
├── Sulfur.exe           ← double-click to launch
├── _internal/           ← app files (do not touch)
├── bin/                 ← llama.cpp binaries
├── preferences.json     ← created after first run (your settings)
├── memory.json          ← created after first run (chat history)
└── sessions/            ← created after first run (saved sessions)
```

Everything is self-contained. No installer, no registry keys, no Python. Just unzip and run.

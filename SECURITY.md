# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Sulfur, please report it privately instead of opening a public issue.

Email: [INSERT YOUR EMAIL]

Please include:
- A clear description of the issue
- Steps to reproduce
- Affected version(s)

I'll respond within 48 hours and work with you on a fix.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Security Design

- Sulfur runs entirely on your machine. No telemetry, no analytics, no data ever leaves your PC.
- Backend connections (llama.cpp, LM Studio, Ollama) are local-only (127.0.0.1).
- API keys, if configured, are stored in `preferences.json` in the app directory. Do not share this file.

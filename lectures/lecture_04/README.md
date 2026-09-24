# Lecture 4

The workspace-wide class conventions are in `../../AGENTS.md`. This README
adds the Lecture 4-specific environment and dependency instructions.

## Setup

From the workspace root:

```zsh
python3 -m venv lectures/lecture_04/.venv
source lectures/lecture_04/.venv/bin/activate
python -m pip install -r lectures/lecture_04/requirements.txt
```

This project uses `pydantic-ai-slim[openai]`, the lightweight PydanticAI
package with OpenAI support. It avoids the larger full `pydantic-ai` install
and unrelated provider, MCP, Logfire, and integration extras.

The small `check_yfinance.py` script verifies that Yahoo Finance price data is
available for an approved ticker before the agent is built.

The root `.env` should contain the Portkey configuration without being copied
into the project or committed:

```dotenv
PORTKEY_API_KEY=your_key_here
PORTKEY_BASE_URL=https://api.portkey.ai/v1
OPENAI_MODEL=gpt-5.6-luna
```

## Dash run rules

Run Dash with `use_reloader=False` or with debug mode off. This prevents one
edit from spawning multiple servers. When stopping the app, terminate the
whole process tree, not just whichever process is listening on port 8050.

On macOS, inspect the port with:

```zsh
lsof -nP -iTCP:8050 -sTCP:LISTEN
```

Then stop the identified application process and its children before starting
again. On Windows, the equivalent is:

```powershell
netstat -ano | findstr :8050
taskkill /PID <pid> /F
```

## Syncing

Pause Dropbox or OneDrive syncing, or exclude `.venv`, while creating the
environment and installing packages. Live syncing can interfere with virtual
environment files and incomplete installs.

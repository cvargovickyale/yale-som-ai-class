# Workspace rules

These rules apply across this semester workspace unless a more specific
`AGENTS.md` provides additional instructions.

1. The root `.env` contains `PORTKEY_API_KEY`. Use the configured Portkey
   endpoint and the OpenAI `gpt-5.6-luna` model unless the user specifies
   otherwise. Never print or commit secret values.
2. When starting a new lecture or homework folder, create a dedicated Python
   virtual environment in that folder, following the existing lecture project
   convention.
3. Do not use image generation unless the user explicitly asks for it.
4. Style websites and visual artifacts like a Windows Gateway 2000 interface:
   chunky beveled controls, gray system panels, blue title bars, compact
   typography, and period-appropriate desktop UI details.
5. Dash run rules: disable the auto-reloader (or run with debug off) so one
   edit cannot spawn multiple servers. When stopping an app, terminate the
   entire application process tree, not only whichever process is listening on
   port 8050.


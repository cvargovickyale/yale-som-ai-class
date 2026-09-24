# Lecture 2 leases

## Setup

From the workspace root:

```zsh
source lectures/lecture_02/.venv/bin/activate
python -m pip install -r lectures/lecture_02/code/requirements.txt
```

The root `.env` must contain `PORTKEY_API_KEY`. The model defaults to `gpt-5.6-luna`; set
`OPENAI_MODEL` in `.env` if your Portkey configuration uses a different model or virtual key.

## Build the JSON

```zsh
python lectures/lecture_02/code/extract_leases.py
```

This reads PDFs from `data/` and writes `leases.json`.

## Run the dashboard

```zsh
python lectures/lecture_02/code/app.py
```

Open http://127.0.0.1:8050 in a browser.

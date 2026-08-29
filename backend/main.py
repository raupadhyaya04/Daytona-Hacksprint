"""Entrypoint for the Agent Red-Team Arena backend.

    python main.py            # run the API on :8000
    MOCK=1 python main.py     # run with the scripted mock (no API keys)

Equivalent to `uvicorn app:app`. See README.md for details.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)

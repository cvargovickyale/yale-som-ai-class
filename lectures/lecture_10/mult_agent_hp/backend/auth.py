"""Shared-password gate for the deployed site.

If APP_PASSWORD is set (on Render), every /api/chat* request must send the same
value in the X-App-Password header. If it's unset (local dev), the gate is off.
Health and roster stay open so the dashboard can render before login.
"""

from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

HEADER = "x-app-password"
PROTECTED_PREFIX = "/api/chat"


def _password() -> str:
    return os.getenv("APP_PASSWORD", "").strip()


def _matches(given: str | None) -> bool:
    expected = _password()
    return bool(given) and hmac.compare_digest(given.encode(), expected.encode())


class PasswordCheck(BaseModel):
    password: str


def install_password_gate(app: FastAPI) -> None:
    @app.middleware("http")
    async def require_password(request: Request, call_next):
        if (
            _password()
            and request.url.path.startswith(PROTECTED_PREFIX)
            and request.method != "OPTIONS"  # let CORS preflight through
            and not _matches(request.headers.get(HEADER))
        ):
            return JSONResponse({"detail": "Password required"}, status_code=401)
        return await call_next(request)

    @app.get("/api/auth/status")
    def auth_status():
        return {"password_required": bool(_password())}

    @app.post("/api/auth/check")
    def auth_check(body: PasswordCheck):
        ok = not _password() or _matches(body.password)
        return JSONResponse({"ok": ok}, status_code=200 if ok else 401)

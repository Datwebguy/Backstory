"""Google sign-in.

Session cookie (signed, not server-stored) is the only source of
user_key for authenticated API calls -- a client can never claim to be
someone else's user_key, unlike the earlier localStorage-only scheme.
"""

from __future__ import annotations

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from backstory.config import Settings

router = APIRouter()


def register_oauth(settings: Settings) -> OAuth:
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


def current_user(request: Request) -> dict | None:
    user_key = request.session.get("user_key")
    if not user_key:
        return None
    return {
        "user_key": user_key,
        "name": request.session.get("name") or "",
        "email": request.session.get("email") or "",
        "picture": request.session.get("picture") or "",
    }


def require_user(request: Request) -> str:
    user = current_user(request)
    if not user:
        raise HTTPException(401, "Sign in required")
    return user["user_key"]


@router.get("/api/me")
def me(request: Request) -> dict:
    user = current_user(request)
    return {"authenticated": bool(user), **(user or {})}


@router.get("/auth/google/login")
async def google_login(request: Request, next: str = "/app"):
    if not request.app.state.oauth.google.client_id:
        raise HTTPException(500, "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not configured")
    request.session["post_login_redirect"] = next
    redirect_uri = str(request.url_for("google_callback"))
    return await request.app.state.oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def google_callback(request: Request):
    token = await request.app.state.oauth.google.authorize_access_token(request)
    claims = token.get("userinfo") or {}
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(400, "Google did not return an account id")
    request.session["user_key"] = f"google:{sub}"
    request.session["name"] = claims.get("name") or ""
    request.session["email"] = claims.get("email") or ""
    request.session["picture"] = claims.get("picture") or ""
    dest = request.session.pop("post_login_redirect", "/app")
    return RedirectResponse(dest)


@router.get("/auth/logout")
def logout(request: Request, next: str = "/"):
    request.session.clear()
    return RedirectResponse(next)

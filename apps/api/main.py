import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from authlib.integrations.base_client.errors import OAuthError
from starlette.middleware.sessions import SessionMiddleware

from apps.api.database import SessionLocal, get_db
from apps.api.models import AuthSession, User
from apps.api.applications import router as applications_router
from apps.api.dependencies import current_user


# Finds and loads apps/api/.env.
env_file = Path(__file__).resolve().parent / ".env"
load_dotenv(env_file)


# Creates the FastAPI application.
session_secret = os.getenv("SESSION_SECRET", "")
if len(session_secret) < 32:
    raise RuntimeError("SESSION_SECRET must contain at least 32 random characters")
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
production = os.getenv("APP_ENV", "development") == "production"
if production and not frontend_url.startswith("https://"):
    raise RuntimeError("Production FRONTEND_URL must use HTTPS")
app = FastAPI(title="FlowState API")
app.include_router(applications_router)


@app.middleware("http")
async def protect_mutations(request: Request, call_next):
    # Browsers always supply Origin on cross-origin fetch mutations. Reject
    # absent/foreign origins instead of relying solely on SameSite cookies.
    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        if request.headers.get("origin") != frontend_url:
            return JSONResponse({"detail": "Untrusted request origin"}, status_code=403)
    return await call_next(request)



# Allows the frontend on localhost:3000 to communicate with
# the backend on localhost:8000.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Allows FastAPI to store login session data in a signed browser cookie.
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    https_only=production,
    same_site="lax",
    max_age=60 * 60 * 12,
)


# Google OAuth setup.
oauth = OAuth()

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=(
        "https://accounts.google.com/.well-known/openid-configuration"
    ),
    client_kwargs={
        "scope": "openid email profile",
    },
)


# Basic route used to verify that the backend is running.
@app.get("/")
def read_root():
    return {"message": "FlowState API is running"}


# -------------------------
# Google OAuth routes
# -------------------------


# Starts the Google login process.
@app.get("/auth/google/login")
async def google_login(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    if not redirect_uri:
        raise HTTPException(503, "Google login is not configured")

    return await oauth.google.authorize_redirect(request, redirect_uri)


# Google sends the user back to this route after a successful login.
@app.get("/auth/google/callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        request.session.clear()
        raise HTTPException(400, "Google authentication failed; please try again") from None
    user_info = token.get("userinfo")

    if not user_info or not user_info.get("sub") or not user_info.get("email_verified"):
        request.session.clear()
        raise HTTPException(400, "A verified Google email is required")

    # Opens a database session.
    with SessionLocal() as database:
        # Searches for a user with this Google account ID.
        database_user = database.scalar(
            select(User).where(User.google_id == user_info["sub"])
        )

        # If no matching user exists, this is their first login.
        if database_user is None:
            database_user = User(
                google_id=user_info["sub"],
                email=user_info["email"],
                name=user_info.get("name"),
            )

            database.add(database_user)

        else:
            # Keeps the saved information current if the user's
            # Google name or email has changed.
            database_user.email = user_info["email"]
            database_user.name = user_info.get("name")

        # Permanently saves the new or updated user.
        database.commit()

        # Reloads the record so generated values such as id are available.
        database.refresh(database_user)

        # Only an opaque session token reaches the browser; logout revokes it.
        session_token = secrets.token_urlsafe(32)
        database.add(AuthSession(
            token_hash=hashlib.sha256(session_token.encode()).hexdigest(),
            user_id=database_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=12),
        ))
        database.commit()

    # Stores basic user information in the signed session cookie.
    request.session.clear()
    request.session["sid"] = session_token

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}/dashboard")


# The database remains the source of truth for account existence.
@app.get("/auth/me")
def auth_me(user: User = Depends(current_user)):
    return {"authenticated": True, "user": {
        "id": user.id, "email": user.email, "name": user.name,
        "google_id": user.google_id,
    }}


# Logs the user out.
@app.post("/auth/logout")
def logout(request: Request, database: Session = Depends(get_db)):
    token = request.session.get("sid")
    if isinstance(token, str):
        database.execute(delete(AuthSession).where(
            AuthSession.token_hash == hashlib.sha256(token.encode()).hexdigest()
        ))
        database.commit()
    request.session.clear()
    return {"message": "Logged out"}


@app.get("/health/live")
def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
def readiness():
    try:
        with SessionLocal() as database:
            database.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable") from None
    return {"status": "ready"}

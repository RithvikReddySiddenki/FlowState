"""Opt-in authenticated Pub/Sub wakeups; notifications never contain message bodies."""

import base64
import json
import os
import time
from functools import lru_cache

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from joserfc import jwt
from joserfc.jwk import KeySet
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from apps.api.database import get_db
from apps.api.gmail_routes import start_sync
from apps.api.models import OAuthCredential, User

router = APIRouter(tags=["gmail-push"])


def enabled():
    return os.getenv("ENABLE_GMAIL_PUSH", "false").lower() == "true"


@lru_cache(maxsize=2)
def signing_keys(hour):
    response = httpx.get("https://www.googleapis.com/oauth2/v3/certs", timeout=10)
    response.raise_for_status()
    return response.json()


def verify_push(authorization):
    audience = os.getenv("GMAIL_PUSH_AUDIENCE", "")
    account = os.getenv("GMAIL_PUSH_SERVICE_ACCOUNT", "")
    if not audience or not account:
        raise HTTPException(503, "Push authentication is not configured")
    if not authorization.startswith("Bearer ") or len(authorization) > 8192:
        raise HTTPException(401, "Invalid push authentication")
    try:
        claims = jwt.decode(
            authorization[7:],
            KeySet.import_key_set(signing_keys(int(time.time() // 3600))),
            algorithms=["RS256"],
        ).claims
        jwt.JWTClaimsRegistry(
            leeway=30,
            iss={
                "essential": True,
                "values": ["https://accounts.google.com", "accounts.google.com"],
            },
            aud={"essential": True, "value": audience},
            exp={"essential": True},
            iat={"essential": True},
        ).validate(claims)
        if claims.get("email") != account or claims.get("email_verified") is not True:
            raise ValueError("Unexpected service identity")
    except httpx.HTTPError:
        raise HTTPException(503, "Push authentication temporarily unavailable") from None
    except Exception:
        raise HTTPException(401, "Invalid push authentication") from None


@router.post("/gmail/push", status_code=204, include_in_schema=False)
async def receive_push(request: Request, database: Session = Depends(get_db)):
    if not enabled():
        raise HTTPException(404, "Not found")
    await run_in_threadpool(verify_push, request.headers.get("authorization", ""))
    # Bound both streamed and Content-Length-free bodies before JSON decoding.
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 16384:
            raise HTTPException(413, "Notification too large")
    try:
        envelope = json.loads(body)
        if not isinstance(envelope, dict):
            raise ValueError("Invalid envelope")
        if envelope.get("subscription") != os.environ["GMAIL_PUSH_SUBSCRIPTION"]:
            raise ValueError("Unexpected subscription")
        encoded = envelope["message"]["data"]
        if not isinstance(encoded, str):
            raise ValueError("Invalid encoded data")
        payload = json.loads(
            base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
        )
        email = payload["emailAddress"]
        history_id = str(payload["historyId"])
        if (
            not isinstance(email, str)
            or len(email) > 320
            or not history_id.isdecimal()
            or len(history_id) > 100
        ):
            raise ValueError("Invalid notification")
    except (ValueError, KeyError, TypeError):
        raise HTTPException(400, "Invalid notification") from None
    user = database.scalar(select(User).where(User.email == email).with_for_update())
    if user is None:
        return Response(status_code=204)
    credential = database.get(OAuthCredential, user.id)
    if credential is None or (
        credential.history_id and int(history_id) <= int(credential.history_id)
    ):
        return Response(status_code=204)
    credential.notified_history_id = history_id
    # The existing single-active-run guard and durable recovery handle duplicates
    # and publication failures. Only a successful worker advances history_id.
    start_sync(database, user)
    return Response(status_code=204)

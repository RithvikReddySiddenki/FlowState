import hashlib
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.api.database import get_db
from apps.api.models import AuthSession, User


def current_user(request: Request, database: Session = Depends(get_db)) -> User:
    token = request.session.get("sid")
    record = (
        database.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
        if isinstance(token, str)
        else None
    )
    expiry = record.expires_at if record else None
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry is None or expiry <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Sign in to continue")
    user = database.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return user

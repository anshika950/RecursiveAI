"""Google OAuth2 login.

Fully coded end-to-end (redirect -> code exchange -> userinfo -> find-or-
create user -> issue the same JWT shape as /auth/login), but it needs a
real GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET from Google Cloud Console to
actually authenticate anyone -- that's a credential only the project
owner can create, not something a backend engineer can fabricate. Both
endpoints below check for that config up front and return a clear 503
instead of crashing on an empty client_id.

Only Google is implemented. GitHub's OAuth2 flow is the same three-step
dance (authorize URL -> code exchange -> userinfo) with different URLs
and field names -- a mechanical follow-up, not a new design, if ever
wanted.
"""

from datetime import timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import create_access_token
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import Token

router = APIRouter(prefix="/auth/oauth/google", tags=["oauth"])

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Not a valid password hash -- verify_password() treats it as "wrong
# password" rather than crashing, so an OAuth-only account can never be
# logged into via POST /auth/login.
OAUTH_ONLY_SENTINEL_PASSWORD = "OAUTH_ACCOUNT_NO_PASSWORD_LOGIN"


def _require_google_configured():
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and "
                "GOOGLE_CLIENT_SECRET (see .env.example)."
            ),
        )


@router.get("/login")
def google_login():
    _require_google_configured()
    params = (
        f"response_type=code&client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&scope=openid%20email%20profile"
    )
    return RedirectResponse(url=f"{GOOGLE_AUTHORIZE_URL}?{params}")


@router.get("/callback", response_model=Token)
async def google_callback(code: str, db: Session = Depends(get_db)):
    _require_google_configured()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            google_tokens = token_response.json()

            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_tokens['access_token']}"},
            )
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Google OAuth exchange failed: {exc.response.text}",
            ) from exc

    email = userinfo.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Google did not return an email")

    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        username = email.split("@")[0]
        # Guard against colliding with an existing username.
        base_username, suffix = username, 1
        while db.query(User).filter(User.username == username).first():
            suffix += 1
            username = f"{base_username}{suffix}"

        db_user = User(
            username=username,
            email=email,
            hashed_password=OAUTH_ONLY_SENTINEL_PASSWORD,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": db_user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException

from .config import APP_PASSWORD_HASH, SECRET_KEY, SESSION_COOKIE, SESSION_MAX_AGE

serializer = URLSafeTimedSerializer(SECRET_KEY)


def check_password(password: str) -> bool:
    if not APP_PASSWORD_HASH:
        return False
    return bcrypt.checkpw(password.encode(), APP_PASSWORD_HASH.encode())


def create_session_token() -> str:
    return serializer.dumps({"admin": True})


def verify_session_token(token: str) -> bool:
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return bool(data.get("admin"))
    except (BadSignature, SignatureExpired):
        return False


def require_login(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token or not verify_session_token(token):
        raise HTTPException(status_code=401, detail="Belum login")
    return True

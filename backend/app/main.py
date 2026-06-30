from fastapi import FastAPI, Response, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .database import init_db
from .auth import check_password, create_session_token, require_login
from .config import SESSION_COOKIE, SESSION_MAX_AGE, TEMPLATES_DIR, SUBMISSIONS_DIR
from .templates_api import router as templates_router
from .submissions_api import router as submissions_router

app = FastAPI(title="SelfieTor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://192.168.1.19:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/templates", StaticFiles(directory=TEMPLATES_DIR), name="templates")
app.mount("/static/submissions", StaticFiles(directory=SUBMISSIONS_DIR), name="submissions")
app.include_router(templates_router)
app.include_router(submissions_router)


@app.on_event("startup")
def on_startup():
    init_db()


class LoginPayload(BaseModel):
    password: str


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/login")
def login(payload: LoginPayload, response: Response):
    if not check_password(payload.password):
        return JSONResponse(status_code=401, content={"detail": "Password salah"})

    token = create_session_token()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return {"status": "ok"}


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "ok"}


@app.get("/api/me")
def me(_: bool = Depends(require_login)):
    return {"admin": True}


@app.get("/api/protected-test")
def protected_test(_: bool = Depends(require_login)):
    return {"message": "Berhasil akses endpoint protected"}

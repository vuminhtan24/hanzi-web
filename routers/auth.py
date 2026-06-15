from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from models.database import get_db, User
from models.auth import verify_password, get_password_hash, create_access_token
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str

@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")
    user = User(
        name=req.name,
        email=req.email,
        password_hash=get_password_hash(req.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    response = JSONResponse({"message": "Đăng ký thành công", "user": {"id": user.id, "name": user.name, "email": user.email, "is_admin": user.is_admin}})
    response.set_cookie("access_token", token, httponly=True, max_age=60*60*24*7, samesite="lax")
    return response

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    token = create_access_token({"sub": str(user.id)})
    response = JSONResponse({"message": "Đăng nhập thành công", "user": {"id": user.id, "name": user.name, "email": user.email, "is_admin": user.is_admin}})
    response.set_cookie("access_token", token, httponly=True, max_age=60*60*24*7, samesite="lax")
    return response

@router.post("/logout")
def logout():
    response = JSONResponse({"message": "Đăng xuất thành công"})
    response.delete_cookie("access_token")
    return response

@router.get("/me")
def get_me(request: Request, db: Session = Depends(get_db)):
    from models.auth import get_current_user_optional
    user = get_current_user_optional(request, db)
    if not user:
        return JSONResponse({"user": None})
    return JSONResponse({"user": {"id": user.id, "name": user.name, "email": user.email, "avatar": user.avatar, "is_admin": user.is_admin}})

@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    # In production: send real email. Here we simulate.
    return JSONResponse({"message": "Nếu email tồn tại, chúng tôi đã gửi link đặt lại mật khẩu"})
import httpx
import os

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")

@router.get("/google")
def google_login():
    redirect_uri = f"{FRONTEND_URL}/api/auth/google/callback"
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=openid email profile"
    )
    return RedirectResponse(url)

@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    redirect_uri = f"{FRONTEND_URL}/api/auth/google/callback"

    # Đổi code lấy token
    async with httpx.AsyncClient() as client:
        token_res = await client.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        token_data = token_res.json()

        # Lấy thông tin user
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
        google_user = user_res.json()

    # Tìm hoặc tạo user
    user = db.query(User).filter(User.email == google_user["email"]).first()
    if not user:
        user = User(
            name=google_user.get("name", ""),
            email=google_user["email"],
            avatar=google_user.get("picture"),
            oauth_provider="google",
            oauth_id=google_user["sub"],
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    response = RedirectResponse(url="/")
    response.set_cookie("access_token", token, httponly=True, max_age=60*60*24*7, samesite="lax")
    return response
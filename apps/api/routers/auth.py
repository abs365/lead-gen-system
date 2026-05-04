from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal
import hashlib
import secrets
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    # Support both sha256 (new) and bcrypt (old)
    sha256_hash = hashlib.sha256(password.encode()).hexdigest()
    if sha256_hash == hashed:
        return True
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateUserRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "user"

@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    from sqlalchemy import text

    result = db.execute(
        text("SELECT id, email, password_hash, name, role, is_active FROM users WHERE email = :email"),
        {"email": data.email.lower().strip()}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id, email, password_hash, name, role, is_active = result

    if not is_active:
        raise HTTPException(status_code=401, detail="Account disabled")

    if not verify_password(data.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create session token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)

    db.execute(
        text("INSERT INTO sessions (user_id, token, expires_at) VALUES (:user_id, :token, :expires_at)"),
        {"user_id": user_id, "token": token, "expires_at": expires_at}
    )

    # Update last login
    db.execute(
        text("UPDATE users SET last_login = NOW() WHERE id = :id"),
        {"id": user_id}
    )

    db.commit()

    return {
        "token": token,
        "user": {"id": user_id, "email": email, "name": name, "role": role}
    }

@router.post("/verify")
def verify_token(data: dict, db: Session = Depends(get_db)):
    from sqlalchemy import text

    token = data.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="No token")

    result = db.execute(
        text("""
            SELECT u.id, u.email, u.name, u.role, u.is_active, s.expires_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = :token
        """),
        {"token": token}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id, email, name, role, is_active, expires_at = result

    if not is_active:
        raise HTTPException(status_code=401, detail="Account disabled")

    if expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired")

    return {"valid": True, "user": {"id": user_id, "email": email, "name": name, "role": role}}

@router.post("/logout")
def logout(data: dict, db: Session = Depends(get_db)):
    from sqlalchemy import text
    token = data.get("token")
    if token:
        db.execute(text("DELETE FROM sessions WHERE token = :token"), {"token": token})
        db.commit()
    return {"success": True}

@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    from sqlalchemy import text
    results = db.execute(
        text("SELECT id, email, name, role, is_active, created_at, last_login FROM users ORDER BY created_at DESC")
    ).fetchall()
    return [
        {"id": r[0], "email": r[1], "name": r[2], "role": r[3], "is_active": r[4], "created_at": str(r[5]), "last_login": str(r[6]) if r[6] else None}
        for r in results
    ]

@router.post("/users")
def create_user(data: CreateUserRequest, db: Session = Depends(get_db)):
    from sqlalchemy import text
    password_hash = hash_password(data.password)
    try:
        db.execute(
            text("INSERT INTO users (email, password_hash, name, role) VALUES (:email, :password_hash, :name, :role)"),
            {"email": data.email.lower().strip(), "password_hash": password_hash, "name": data.name, "role": data.role}
        )
        db.commit()
        return {"success": True, "message": f"User {data.email} created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"User already exists or error: {str(e)}")

@router.post("/users/{user_id}/toggle")
def toggle_user(user_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import text
    db.execute(
        text("UPDATE users SET is_active = NOT is_active WHERE id = :id"),
        {"id": user_id}
    )
    db.commit()
    return {"success": True}

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import text
    db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    db.commit()
    return {"success": True}
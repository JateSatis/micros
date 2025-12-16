from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
from datetime import datetime
from typing import Optional
import os
import uuid

app = FastAPI()
security = HTTPBearer()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://verif_user:verif_pass@localhost:5432/verification_db")
JWT_SECRET = os.getenv("JWT_SECRET", "secret_key_for_jwt")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Verification(Base):
    __tablename__ = "verifications"
    
    id = Column(String, primary_key=True, default=lambda: f"verif-{uuid.uuid4()}")
    user_id = Column(String, nullable=False, index=True)
    first_name = Column(String)
    last_name = Column(String)
    middle_name = Column(String)
    series = Column(String)
    number = Column(String)
    issued_by = Column(String)
    issued_date = Column(String)
    citizenship = Column(String)
    status = Column(String, default="pending")
    reason = Column(Text)
    verified_at = Column(DateTime, nullable=True)
    passport_valid = Column(Boolean, nullable=True)
    matches_registry = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_user_id(token_data: dict = Depends(verify_token)):
    return token_data.get("sub")


class PassportData(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    series: str
    number: str
    issued_by: str
    issued_date: str
    citizenship: str


@app.post("/api/verification/passport")
async def submit_passport(
    request: PassportData,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    # Проверка на активную верификацию
    active_verification = db.query(Verification).filter(
        Verification.user_id == user_id,
        Verification.status.in_(["pending", "verified"])
    ).first()
    
    if active_verification:
        raise HTTPException(
            status_code=409,
            detail="Active verification already exists for this user"
        )
    
    # Создание запроса на верификацию
    verification = Verification(
        user_id=user_id,
        first_name=request.first_name,
        last_name=request.last_name,
        middle_name=request.middle_name,
        series=request.series,
        number=request.number,
        issued_by=request.issued_by,
        issued_date=request.issued_date,
        citizenship=request.citizenship,
        status="pending"
    )
    db.add(verification)
    db.commit()
    db.refresh(verification)
    
    # Упрощенная симуляция отправки во внешний сервис
    # В реальности здесь должен быть HTTP запрос к внешнему API
    try:
        # Симуляция успешной отправки
        # В реальности может быть ошибка 422
        pass
    except Exception:
        db.delete(verification)
        db.commit()
        raise HTTPException(
            status_code=422,
            detail="Failed to send data to external service"
        )
    
    return {
        "verification_id": verification.id,
        "status": verification.status,
        "message": "Verification request submitted successfully"
    }


@app.get("/api/verification/passport/{verification_id}")
async def get_verification_status(
    verification_id: str,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    verification = db.query(Verification).filter(Verification.id == verification_id).first()
    
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    # Проверка прав доступа
    if verification.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied to this verification")
    
    # Симуляция верификации (в реальности статус приходит от внешнего сервиса)
    if verification.status == "pending":
        # Автоматически помечаем как verified через некоторое время
        # В реальности это должно приходить от внешнего сервиса
        verification.status = "verified"
        verification.verified_at = datetime.utcnow()
        verification.passport_valid = True
        verification.matches_registry = True
        db.commit()
    
    if verification.status == "verified":
        return {
            "verification_id": verification.id,
            "status": verification.status,
            "verified_at": verification.verified_at.isoformat() + "Z" if verification.verified_at else None,
            "details": {
                "first_name": verification.first_name,
                "last_name": verification.last_name,
                "citizenship": verification.citizenship,
                "passport_valid": verification.passport_valid,
                "matches_registry": verification.matches_registry
            }
        }
    else:
        return {
            "verification_id": verification.id,
            "status": verification.status,
            "reason": verification.reason or "Passport verification failed"
        }


@app.get("/health")
async def health():
    return {"status": "ok"}

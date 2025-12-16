from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
from datetime import datetime
from typing import Optional
import os
import uuid

app = FastAPI()
security = HTTPBearer()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mailing_user:mailing_pass@localhost:5432/mailing_db")
JWT_SECRET = os.getenv("JWT_SECRET", "secret_key_for_jwt")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, nullable=False, index=True)
    subscribed = Column(Boolean, default=True)
    categories = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmailMessage(Base):
    __tablename__ = "email_messages"
    
    id = Column(String, primary_key=True, default=lambda: f"mail-{uuid.uuid4()}")
    to_email = Column(String, nullable=False)
    subject = Column(String)
    body = Column(Text)
    template_id = Column(String)
    variables = Column(JSON)
    status = Column(String, default="queued")
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


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


class UnsubscribeRequest(BaseModel):
    email: EmailStr
    categories: list[str]


class SubscribeRequest(BaseModel):
    email: EmailStr
    categories: list[str]


class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: Optional[str] = None
    template_id: Optional[str] = None
    variables: Optional[dict] = None


@app.post("/api/mailing/unsubscribe")
async def unsubscribe(
    request: UnsubscribeRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    subscription = db.query(Subscription).filter(Subscription.email == request.email).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="User not found")
    
    subscription.subscribed = False
    subscription.categories = request.categories
    
    db.commit()
    
    return {
        "email": subscription.email,
        "subscribed": subscription.subscribed,
        "categories": subscription.categories,
        "message": "You have successfully unsubscribed from mailing list"
    }


@app.post("/api/mailing/subscribe")
async def subscribe(
    request: SubscribeRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    subscription = db.query(Subscription).filter(Subscription.email == request.email).first()
    
    if subscription and subscription.subscribed:
        raise HTTPException(status_code=409, detail="User already subscribed")
    
    if subscription:
        subscription.subscribed = True
        subscription.categories = request.categories
    else:
        subscription = Subscription(
            email=request.email,
            subscribed=True,
            categories=request.categories
        )
        db.add(subscription)
    
    db.commit()
    db.refresh(subscription)
    
    return {
        "email": subscription.email,
        "subscribed": subscription.subscribed,
        "categories": subscription.categories,
        "message": "You have successfully subscribed from mailing list"
    }


@app.post("/api/mailing/send")
async def send_email(
    request: SendEmailRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    # Проверка шаблона (упрощенная)
    if request.template_id and request.template_id not in ["welcome-template", "notification-template"]:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    # Создание записи о письме
    email_message = EmailMessage(
        to_email=request.to,
        subject=request.subject,
        body=request.body,
        template_id=request.template_id,
        variables=request.variables,
        status="queued"
    )
    db.add(email_message)
    db.commit()
    db.refresh(email_message)
    
    # В реальности здесь должна быть отправка письма через SMTP или email-сервис
    # Для простоты просто помечаем как отправленное
    email_message.status = "sent"
    email_message.sent_at = datetime.utcnow()
    db.commit()
    
    return {
        "message_id": email_message.id,
        "status": email_message.status,
        "sent_at": email_message.sent_at.isoformat() + "Z" if email_message.sent_at else None
    }


@app.get("/health")
async def health():
    return {"status": "ok"}

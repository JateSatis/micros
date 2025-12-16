from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
from datetime import datetime
from prometheus_fastapi_instrumentator import Instrumentator
from typing import Optional
import logging
import os
import uuid

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()
security = HTTPBearer()

# Настройка Prometheus метрик
instrumentator = Instrumentator()
instrumentator.instrument(app)
instrumentator.expose(app)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://notif_user:notif_pass@localhost:5432/notifications_db")
JWT_SECRET = os.getenv("JWT_SECRET", "secret_key_for_jwt")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Device(Base):
    __tablename__ = "devices"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    push_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, default=lambda: f"notif-{uuid.uuid4()}")
    user_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    type = Column(String)
    data = Column(JSON)
    status = Column(String, default="sent")
    sent_at = Column(DateTime, default=datetime.utcnow)
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


class DeviceRequest(BaseModel):
    device_id: str


class SendNotificationRequest(BaseModel):
    user_id: str
    title: str
    body: str
    type: str
    data: Optional[dict] = None


@app.post("/api/notifications/disable")
async def disable_notifications(
    request: DeviceRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.device_id == request.device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Проверка прав
    if device.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    device.push_enabled = False
    db.commit()
    
    return {
        "user_id": f"user-{device.user_id}",
        "device_id": device.device_id,
        "push_enabled": device.push_enabled,
        "message": "Push notifications disabled successfully"
    }


@app.post("/api/notifications/enable")
async def enable_notifications(
    request: DeviceRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.device_id == request.device_id).first()
    
    if not device:
        # Создаем новое устройство
        device = Device(
            device_id=request.device_id,
            user_id=user_id,
            push_enabled=True
        )
        db.add(device)
    else:
        # Проверка прав
        if device.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        device.push_enabled = True
    
    db.commit()
    db.refresh(device)
    
    return {
        "user_id": f"user-{device.user_id}",
        "device_id": device.device_id,
        "push_enabled": device.push_enabled,
        "message": "Push notifications enabled successfully"
    }


@app.post("/api/notifications/send")
async def send_notification(
    request: SendNotificationRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    logger.info(f"Sending notification to user: {request.user_id}, type: {request.type}")
    # Проверка существования пользователя (упрощенная)
    # В реальности нужно проверять через auth-service
    
    # Проверка, что устройство включено
    devices = db.query(Device).filter(
        Device.user_id == request.user_id,
        Device.push_enabled == True
    ).all()
    
    if not devices:
        # В реальности может быть ошибка, но для простоты продолжаем
        logger.warning(f"No enabled devices found for user: {request.user_id}")
    
    # Создание уведомления
    notification = Notification(
        user_id=request.user_id,
        title=request.title,
        body=request.body,
        type=request.type,
        data=request.data,
        status="sent"
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    # В реальности здесь должна быть отправка через FCM, APNS и т.д.
    logger.info(f"Notification sent successfully: {notification.id}")
    return {
        "notification_id": notification.id,
        "status": notification.status,
        "sent_at": notification.sent_at.isoformat() + "Z"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


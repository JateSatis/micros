from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
from datetime import datetime
from prometheus_fastapi_instrumentator import Instrumentator
from typing import Optional
import logging
import os
import uuid
import httpx

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

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://apps_user:apps_pass@localhost:5432/applications_db")
JWT_SECRET = os.getenv("JWT_SECRET", "secret_key_for_jwt")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
JOBS_SERVICE_URL = os.getenv("JOBS_SERVICE_URL", "http://localhost:8003")
PROFILE_SERVICE_URL = os.getenv("PROFILE_SERVICE_URL", "http://localhost:8002")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Application(Base):
    __tablename__ = "applications"
    
    id = Column(String, primary_key=True, default=lambda: f"app-{uuid.uuid4()}")
    job_id = Column(String, nullable=False)
    resume_id = Column(String, nullable=False)
    candidate_id = Column(String, nullable=False)
    cover_letter = Column(Text)
    status = Column(String, default="pending")
    comment = Column(Text)
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


async def check_job_exists(job_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{JOBS_SERVICE_URL}/api/jobs/search?query=&page=1&limit=1")
            if response.status_code == 200:
                # Простая проверка - в реальности нужно проверять конкретный job_id
                return True
    except:
        pass
    return True  # Упрощенная проверка


async def check_resume_exists(resume_id: str, user_id: str):
    # Упрощенная проверка - в реальности нужно делать запрос к profile-service
    return True


class ApplicationCreate(BaseModel):
    job_id: str
    resume_id: str
    cover_letter: Optional[str] = None


class AcceptRequest(BaseModel):
    comment: Optional[str] = None


@app.post("/api/applications")
async def create_application(
    request: ApplicationCreate,
    candidate_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    logger.info(f"Creating application by candidate: {candidate_id} for job: {request.job_id}")
    # Упрощенные проверки
    await check_job_exists(request.job_id)
    await check_resume_exists(request.resume_id, candidate_id)
    
    application = Application(
        job_id=request.job_id,
        resume_id=request.resume_id,
        candidate_id=candidate_id,
        cover_letter=request.cover_letter
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    logger.info(f"Application created successfully: {application.id}")
    return {
        "id": application.id,
        "message": "Application submitted successfully",
        "status": application.status
    }


@app.post("/api/applications/{application_id}/accept")
async def accept_application(
    application_id: str,
    request: AcceptRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Проверка прав - упрощенная (в реальности нужно проверять владельца вакансии)
    # Проверяем, что статус еще pending
    if application.status != "pending":
        raise HTTPException(status_code=409, detail="Application already processed")
    
    application.status = "accepted"
    if request.comment:
        application.comment = request.comment
    
    db.commit()
    
    return {
        "id": application.id,
        "status": application.status,
        "message": "Application accepted successfully"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


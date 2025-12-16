from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
from datetime import datetime
from prometheus_fastapi_instrumentator import Instrumentator
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

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://profile_user:profile_pass@localhost:5432/profile_db")
JWT_SECRET = os.getenv("JWT_SECRET", "secret_key_for_jwt")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Profile(Base):
    __tablename__ = "profiles"
    
    user_id = Column(String, primary_key=True)
    email = Column(String)
    phone_number = Column(String)
    passport_series = Column(String)
    passport_number = Column(String)
    passport_issued_by = Column(String)
    passport_issued_date = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    title = Column(String)
    position = Column(String)
    skills = Column(JSON)
    experience = Column(JSON)
    education = Column(JSON)
    description = Column(Text)
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


class PassportUpdate(BaseModel):
    series: str
    number: str
    issued_by: str
    issued_date: str


class EmailUpdate(BaseModel):
    new_email: EmailStr


class PhoneUpdate(BaseModel):
    phone_number: str


class ExperienceItem(BaseModel):
    company: str
    position: str
    start_date: str
    end_date: str
    description: str


class EducationItem(BaseModel):
    institution: str
    degree: str
    year: int


class ResumeCreate(BaseModel):
    title: str
    position: str
    skills: list[str]
    experience: list[ExperienceItem]
    education: list[EducationItem]
    description: str


class ResumeUpdate(BaseModel):
    title: str | None = None
    position: str | None = None
    skills: list[str] | None = None
    experience: list[ExperienceItem] | None = None
    education: list[EducationItem] | None = None
    description: str | None = None


@app.put("/api/profile/passport")
async def update_passport(
    request: PassportUpdate,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    logger.info(f"Updating passport data for user: {user_id}")
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)
    
    profile.passport_series = request.series
    profile.passport_number = request.number
    profile.passport_issued_by = request.issued_by
    profile.passport_issued_date = request.issued_date
    
    db.commit()
    logger.info(f"Passport data updated successfully for user: {user_id}")
    return {"message": "Passport data updated successfully"}


@app.put("/api/profile/email")
async def update_email(
    request: EmailUpdate,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)
    
    profile.email = request.new_email
    db.commit()
    
    return {"message": "Email updated successfully"}


@app.put("/api/profile/phone")
async def update_phone(
    request: PhoneUpdate,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)
    
    profile.phone_number = request.phone_number
    db.commit()
    
    return {"message": "Phone number updated successfully"}


@app.post("/api/profile/resumes")
async def create_resume(
    request: ResumeCreate,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    logger.info(f"Creating resume for user: {user_id}, title: {request.title}")
    resume = Resume(
        user_id=user_id,
        title=request.title,
        position=request.position,
        skills=request.skills,
        experience=[exp.dict() for exp in request.experience],
        education=[edu.dict() for edu in request.education],
        description=request.description
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    logger.info(f"Resume created successfully: r-{resume.id} for user: {user_id}")
    return {"id": f"r-{resume.id}", "message": "Resume created successfully"}


@app.patch("/api/profile/resumes/{resume_id}")
async def update_resume(
    resume_id: str,
    request: ResumeUpdate,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    # Убираем префикс r- если есть
    if resume_id.startswith("r-"):
        resume_id = resume_id[2:]
    
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    if request.title is not None:
        resume.title = request.title
    if request.position is not None:
        resume.position = request.position
    if request.skills is not None:
        resume.skills = request.skills
    if request.experience is not None:
        resume.experience = [exp.dict() for exp in request.experience]
    if request.education is not None:
        resume.education = [edu.dict() for edu in request.education]
    if request.description is not None:
        resume.description = request.description
    
    db.commit()
    
    return {"message": "Resume updated successfully"}


@app.delete("/api/profile/resumes/{resume_id}")
async def delete_resume(
    resume_id: str,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    # Убираем префикс r- если есть
    if resume_id.startswith("r-"):
        resume_id = resume_id[2:]
    
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    db.delete(resume)
    db.commit()
    
    return {"message": "Resume deleted successfully"}


@app.get("/health")
async def health():
    return {"status": "ok"}


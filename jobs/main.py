from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON, Integer, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
from datetime import datetime
from typing import Optional
import os
import uuid

app = FastAPI()
security = HTTPBearer()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://jobs_user:jobs_pass@localhost:5432/jobs_db")
JWT_SECRET = os.getenv("JWT_SECRET", "secret_key_for_jwt")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=lambda: f"job-{uuid.uuid4()}")
    employer_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    requirements = Column(JSON)
    salary = Column(Numeric)
    currency = Column(String)
    location = Column(String)
    employment_type = Column(String)
    company_name = Column(String, default="Unknown Company")
    salary_from = Column(Numeric)
    salary_to = Column(Numeric)
    posted_at = Column(DateTime, default=datetime.utcnow)
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


def check_employer_role(token_data: dict = Depends(verify_token)):
    role = token_data.get("role")
    if role != "employer":
        raise HTTPException(status_code=403, detail="User is not an employer")
    return token_data.get("sub")


class JobCreate(BaseModel):
    title: str
    description: str
    requirements: list[str]
    salary: float
    currency: str
    location: str
    employment_type: str


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[list[str]] = None
    salary: Optional[float] = None
    currency: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None


@app.put("/api/jobs")
async def create_job(
    request: JobCreate,
    employer_id: str = Depends(check_employer_role),
    db: Session = Depends(get_db)
):
    job = Job(
        employer_id=employer_id,
        title=request.title,
        description=request.description,
        requirements=request.requirements,
        salary=request.salary,
        currency=request.currency,
        location=request.location,
        employment_type=request.employment_type,
        salary_from=request.salary,
        salary_to=request.salary
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return {"id": job.id, "message": "Job created successfully"}


@app.put("/api/jobs/{job_id}")
async def update_job_put(
    job_id: str,
    request: JobCreate,
    employer_id: str = Depends(check_employer_role),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id, Job.employer_id == employer_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.title = request.title
    job.description = request.description
    job.requirements = request.requirements
    job.salary = request.salary
    job.currency = request.currency
    job.location = request.location
    job.employment_type = request.employment_type
    job.salary_from = request.salary
    job.salary_to = request.salary
    
    db.commit()
    
    return {"id": job.id, "message": "Job created successfully"}


@app.patch("/api/jobs/{job_id}")
async def update_job(
    job_id: str,
    request: JobUpdate,
    employer_id: str = Depends(check_employer_role),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id, Job.employer_id == employer_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if request.title is not None:
        job.title = request.title
    if request.description is not None:
        job.description = request.description
    if request.requirements is not None:
        job.requirements = request.requirements
    if request.salary is not None:
        job.salary = request.salary
        job.salary_from = request.salary
        job.salary_to = request.salary
    if request.currency is not None:
        job.currency = request.currency
    if request.location is not None:
        job.location = request.location
    if request.employment_type is not None:
        job.employment_type = request.employment_type
    
    db.commit()
    
    return {"id": job.id, "message": "Job updated successfully"}


@app.delete("/api/jobs/{job_id}")
async def delete_job(
    job_id: str,
    employer_id: str = Depends(check_employer_role),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id, Job.employer_id == employer_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    db.delete(job)
    db.commit()
    
    return {"message": "Job deleted successfully"}


@app.get("/api/jobs/search")
async def search_jobs(
    query: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    employment_type: Optional[str] = Query(None),
    salary_from: Optional[float] = Query(None),
    salary_to: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    jobs_query = db.query(Job)
    
    if query:
        jobs_query = jobs_query.filter(
            Job.title.ilike(f"%{query}%") | Job.description.ilike(f"%{query}%")
        )
    if location:
        jobs_query = jobs_query.filter(Job.location.ilike(f"%{location}%"))
    if employment_type:
        jobs_query = jobs_query.filter(Job.employment_type == employment_type)
    if salary_from:
        jobs_query = jobs_query.filter(Job.salary >= salary_from)
    if salary_to:
        jobs_query = jobs_query.filter(Job.salary <= salary_to)
    
    total = jobs_query.count()
    jobs = jobs_query.offset((page - 1) * limit).limit(limit).all()
    
    results = []
    for job in jobs:
        results.append({
            "id": job.id,
            "title": job.title,
            "company_name": job.company_name,
            "location": job.location,
            "salary_from": float(job.salary_from) if job.salary_from else None,
            "salary_to": float(job.salary_to) if job.salary_to else None,
            "currency": job.currency,
            "employment_type": job.employment_type,
            "posted_at": job.posted_at.isoformat() + "Z"
        })
    
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "results": results
    }


@app.get("/health")
async def health():
    return {"status": "ok"}

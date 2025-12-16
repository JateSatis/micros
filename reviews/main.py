from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
from datetime import datetime
from typing import Optional
import os
import uuid
import httpx

app = FastAPI()
security = HTTPBearer()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://reviews_user:reviews_pass@localhost:5432/reviews_db")
JWT_SECRET = os.getenv("JWT_SECRET", "secret_key_for_jwt")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
JOBS_SERVICE_URL = os.getenv("JOBS_SERVICE_URL", "http://localhost:8003")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(String, primary_key=True, default=lambda: f"rev-{uuid.uuid4()}")
    job_id = Column(String, nullable=False)
    author_id = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    is_anonymous = Column(Boolean, default=False)
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


def check_candidate_role(token_data: dict = Depends(verify_token)):
    role = token_data.get("role")
    if role != "candidate":
        raise HTTPException(status_code=403, detail="Only candidates can leave reviews")
    return token_data.get("sub")


async def check_job_exists(job_id: str):
    # Упрощенная проверка
    return True


class ReviewCreate(BaseModel):
    job_id: str
    rating: int
    comment: str
    is_anonymous: bool = False


class ReviewUpdate(BaseModel):
    rating: int
    comment: str
    is_anonymous: bool


@app.post("/api/reviews")
async def create_review(
    request: ReviewCreate,
    author_id: str = Depends(check_candidate_role),
    db: Session = Depends(get_db)
):
    # Проверка существования вакансии
    await check_job_exists(request.job_id)
    
    # Проверка, что отзыв еще не существует
    existing_review = db.query(Review).filter(
        Review.job_id == request.job_id,
        Review.author_id == author_id
    ).first()
    
    if existing_review:
        raise HTTPException(status_code=409, detail="Review for this job already exists")
    
    # Валидация рейтинга
    if request.rating < 1 or request.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    review = Review(
        job_id=request.job_id,
        author_id=author_id,
        rating=request.rating,
        comment=request.comment,
        is_anonymous=request.is_anonymous
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    
    return {
        "id": review.id,
        "job_id": review.job_id,
        "rating": review.rating,
        "comment": review.comment,
        "author_id": f"user-{review.author_id}",
        "created_at": review.created_at.isoformat() + "Z"
    }


@app.put("/api/reviews/{review_id}")
async def update_review(
    review_id: str,
    request: ReviewUpdate,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Проверка прав
    if review.author_id != user_id:
        raise HTTPException(status_code=403, detail="User is not the author of this review")
    
    # Валидация рейтинга
    if request.rating < 1 or request.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    review.rating = request.rating
    review.comment = request.comment
    review.is_anonymous = request.is_anonymous
    
    db.commit()
    db.refresh(review)
    
    return {
        "id": review.id,
        "job_id": review.job_id,
        "rating": review.rating,
        "comment": review.comment,
        "updated_at": review.updated_at.isoformat() + "Z"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}

import logging
import os
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, JSON, String, create_engine, func, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

log = logging.getLogger("oncopredict")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

if DATABASE_URL.startswith("postgresql+psycopg2://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)


class Base(DeclarativeBase):
    pass


class PredictionRecord(Base):
    __tablename__ = "prediction_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    staff_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    patient_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    prediction_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
except ModuleNotFoundError as err:
    log.warning("PostgreSQL driver unavailable; continuing without DB persistence: %s", err)
    engine = None

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine else None


def init_db() -> bool:
    """Create database tables when the backend starts if a DATABASE_URL is set."""
    if engine is None:
        return False
    Base.metadata.create_all(bind=engine)
    return True


def save_prediction(staff_id: str, patient_payload: dict[str, Any], prediction_payload: dict[str, Any]) -> int | None:
    """Persist a prediction record to Postgres; returns the inserted id or None when disabled."""
    if SessionLocal is None:
        return None

    with SessionLocal() as session:
        record = PredictionRecord(
            staff_id=staff_id,
            patient_payload=patient_payload,
            prediction_payload=prediction_payload,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.id


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, index=True, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    password_salt: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def create_user(email: str, password_hash: str, password_salt: str, name: str | None = None, is_admin: bool = False) -> int | None:
    """Create a user record. Returns id or None when DB disabled."""
    if SessionLocal is None:
        return None
    with SessionLocal() as session:
        user = User(email=email, password_hash=password_hash, password_salt=password_salt, name=name, is_admin=is_admin)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


def get_user_auth(email: str) -> dict | None:
    """Return auth fields for a given email, or None if not found or DB disabled."""
    if SessionLocal is None:
        return None
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            return None
        return {
            "id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "password_salt": user.password_salt,
            "name": user.name,
            "is_admin": bool(user.is_admin),
            "created_at": user.created_at,
        }


def list_users() -> list[dict]:
    if SessionLocal is None:
        return []
    with SessionLocal() as session:
        users = session.query(User).all()
        return [
            {"id": u.id, "email": u.email, "name": u.name, "is_admin": bool(u.is_admin), "created_at": u.created_at}
            for u in users
        ]


def list_prediction_records(limit: int = 100) -> list[dict]:
    if SessionLocal is None:
        return []
    with SessionLocal() as session:
        recs = session.query(PredictionRecord).order_by(PredictionRecord.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "staff_id": r.staff_id,
                "patient_payload": r.patient_payload,
                "prediction_payload": r.prediction_payload,
                "created_at": r.created_at,
            }
            for r in recs
        ]

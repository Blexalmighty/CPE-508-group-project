import os
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, JSON, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


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


engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
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

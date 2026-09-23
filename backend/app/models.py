from datetime import datetime, timezone
from sqlalchemy import String, JSON, DateTime, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def now():
    return datetime.now(timezone.utc)

class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    contamination_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(3000))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    segment_id: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(30), default='UNVERIFIED')
    reporter_name: Mapped[str] = mapped_column(String(100), default='')
    contact: Mapped[str] = mapped_column(String(200), default='')
    image_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
    impact: Mapped[dict] = mapped_column(JSON)
    priority_score: Mapped[int] = mapped_column(Integer)
    priority_level: Mapped[str] = mapped_column(String(20))
    timeline: Mapped[list] = mapped_column(JSON, default=list)

class Alert(Base):
    __tablename__ = 'alerts'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    report_id: Mapped[str] = mapped_column(ForeignKey('reports.id'), index=True)
    target: Mapped[str] = mapped_column(String(200))
    target_type: Mapped[str] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(30), default='Generated')
    message: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

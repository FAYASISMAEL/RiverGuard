from datetime import datetime, timezone
from sqlalchemy import String, JSON, DateTime, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
    case_file: Mapped['CaseFile | None'] = relationship(back_populates='report', uselist=False)
    images: Mapped[list['ReportImage']] = relationship(order_by='ReportImage.position', cascade='all, delete-orphan')

class ReportImage(Base):
    __tablename__ = 'report_images'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    report_id: Mapped[str] = mapped_column(ForeignKey('reports.id'), index=True)
    image_url: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer)

class UploadedAsset(Base):
    __tablename__ = 'uploaded_assets'
    name: Mapped[str] = mapped_column(String(80), primary_key=True)
    storage: Mapped[str] = mapped_column(String(20))
    url: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AdminAction(Base):
    __tablename__ = 'admin_actions'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    report_id: Mapped[str] = mapped_column(ForeignKey('reports.id'), index=True)
    action: Mapped[str] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    details: Mapped[dict] = mapped_column(JSON)

class CaseFile(Base):
    __tablename__ = 'case_files'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(ForeignKey('reports.id'), unique=True)
    review_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    report: Mapped['Report'] = relationship(back_populates='case_file')

    @property
    def case_id(self):
        return f'CASE-{self.review_started_at.year}-{self.id:04d}'

class AdminSession(Base):
    __tablename__ = 'admin_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(100))
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Alert(Base):
    __tablename__ = 'alerts'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    report_id: Mapped[str] = mapped_column(ForeignKey('reports.id'), index=True)
    target: Mapped[str] = mapped_column(String(200))
    target_type: Mapped[str] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(30), default='Generated')
    message: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

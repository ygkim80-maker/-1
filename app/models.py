from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    headcount = Column(Integer, nullable=False, default=0)  # 진척률 계산용 예상 인원

    signatures = relationship("Signature", back_populates="site")


class EducationDocument(Base):
    __tablename__ = "education_documents"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    version = Column(String(20), nullable=False, default="1.0")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Signature(Base):
    __tablename__ = "signatures"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("education_documents.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    entered_name = Column(String(50), nullable=False)  # 서명자가 직접 입력한 이름 (본인확인 절차 없음)
    signed_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(64))
    user_agent = Column(String(255))
    signature_image_path = Column(String(255))
    content_hash = Column(String(64))

    document = relationship("EducationDocument")
    site = relationship("Site", back_populates="signatures")

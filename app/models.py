import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    region = Column(String(100))

    drivers = relationship("Driver", back_populates="site")


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    name = Column(String(50), nullable=False)
    employee_no = Column(String(30), nullable=False, unique=True)
    phone = Column(String(20))
    birthdate = Column(String(8))  # YYYYMMDD, 본인확인 용도 (운영 배포 시 암호화 권장)

    site = relationship("Site", back_populates="drivers")
    signing_links = relationship("SigningLink", back_populates="driver")


class EducationDocument(Base):
    __tablename__ = "education_documents"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    version = Column(String(20), nullable=False, default="1.0")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SigningLink(Base):
    __tablename__ = "signing_links"

    id = Column(Integer, primary_key=True)
    token = Column(String(36), nullable=False, unique=True, default=lambda: uuid.uuid4().hex)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("education_documents.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    driver = relationship("Driver", back_populates="signing_links")
    document = relationship("EducationDocument")
    signature = relationship("Signature", back_populates="signing_link", uselist=False)

    __table_args__ = (UniqueConstraint("driver_id", "document_id", name="uq_driver_document"),)


class Signature(Base):
    __tablename__ = "signatures"

    id = Column(Integer, primary_key=True)
    signing_link_id = Column(Integer, ForeignKey("signing_links.id"), nullable=False, unique=True)
    signed_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(64))
    user_agent = Column(String(255))
    verify_method = Column(String(50))
    signature_image_path = Column(String(255))
    content_hash = Column(String(64))

    signing_link = relationship("SigningLink", back_populates="signature")

"""
Database models for MAASTrap
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./maastrap.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """Admin user model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=True)


class UbuntuImage(Base):
    """Ubuntu base image model"""
    __tablename__ = "ubuntu_images"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "Ubuntu 22.04 LTS (Jammy)"
    codename = Column(String, unique=True, nullable=False)  # e.g., "jammy"
    version = Column(String, nullable=False)  # e.g., "22.04"
    iso_path = Column(String, nullable=False)  # Path to stored ISO file
    is_active = Column(Boolean, default=True)
    
    # Relationship to MAAS versions
    maas_versions = relationship("MAASVersion", back_populates="ubuntu_image")


class MAASVersion(Base):
    """MAAS version configuration"""
    __tablename__ = "maas_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, nullable=False)  # e.g., "3.2", "3.3", "3.4"
    ppa_url = Column(String, nullable=False)  # e.g., "ppa:maas/3.2"
    ubuntu_image_id = Column(Integer, ForeignKey("ubuntu_images.id"))
    is_active = Column(Boolean, default=True)
    
    # Relationship to Ubuntu image
    ubuntu_image = relationship("UbuntuImage", back_populates="maas_versions")


def init_db():
    """Initialize database and create default admin user"""
    Base.metadata.create_all(bind=engine)
    
    # Create default admin user if not exists
    from auth import get_password_hash
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@maastrap.local",
                hashed_password=get_password_hash("admin"),  # Default password, should be changed
                is_admin=True
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

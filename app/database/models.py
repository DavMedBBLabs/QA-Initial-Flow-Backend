import enum
import uuid
from sqlalchemy import Column, String, Text, DateTime, Enum, JSON, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .connection import Base, engine

class HUStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relación con proyectos
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=False)  # Solo un proyecto activo por usuario
    
    # Credenciales de Azure DevOps
    azure_devops_token = Column(Text, nullable=False)
    azure_org = Column(String(100), nullable=False)
    azure_project = Column(String(100), nullable=False)
    
    # Credenciales de XRay
    client_id = Column(String(100), nullable=False)
    client_secret = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relación con usuario
    user = relationship("User", back_populates="projects")

class HU(Base):
    __tablename__ = "hus"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    azure_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(HUStatus), default=HUStatus.PENDING, nullable=False)
    refined_response = Column(Text, nullable=True)  # Respuesta refinada en texto plano
    markdown_response = Column(Text, nullable=True)  # Respuesta refinada en Markdown
    feature = Column(String(200), nullable=True)  # Feature a la que pertenece la HU
    module = Column(String(200), nullable=True)  # Módulo al que pertenece la HU
    language = Column(String(10), nullable=True, default='es')  # Idioma de refinamiento ('es' o 'en')
    tests_generated = Column(JSON, nullable=True)  # Tests generados clasificados
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)  # Proyecto al que pertenece la HU
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relación con proyecto
    project = relationship("Project", backref="hus")

# Create tables
Base.metadata.create_all(bind=engine)
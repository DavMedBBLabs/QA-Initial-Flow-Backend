import enum
import uuid
from sqlalchemy import Column, String, Text, DateTime, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .connection import Base, engine

class HUStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

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
    tests_generated = Column(JSON, nullable=True)  # Tests generados clasificados
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

# Create tables
Base.metadata.create_all(bind=engine)
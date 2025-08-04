from pydantic import BaseModel
from typing import Optional, List

class HUCreate(BaseModel):
    azure_id: str
    language: Optional[str] = 'es'  # 'es' = español, 'en' = inglés

class HUStatusUpdate(BaseModel):
    status: str
    feedback: Optional[str] = None

class HUResponse(BaseModel):
    id: str
    azure_id: str
    name: str
    description: Optional[str]
    status: str
    refined_response: Optional[str]  # Cambiado de dict a str
    markdown_response: Optional[str]  # Cambiado de dict a str
    feature: Optional[str]  # Nuevo campo
    module: Optional[str]  # Nuevo campo
    language: Optional[str] = 'es'  # Nuevo campo para idioma
    created_at: Optional[str]
    updated_at: Optional[str]

class HUListResponse(BaseModel):
    data: List[HUResponse]
    message: str

class TestGenerationRequest(BaseModel):
    xray_path: str
    azure_id: str
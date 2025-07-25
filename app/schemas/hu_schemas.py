from pydantic import BaseModel
from typing import Optional

class HUCreate(BaseModel):
    azure_id: str

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
    created_at: Optional[str]
    updated_at: Optional[str]

class TestGenerationRequest(BaseModel):
    xray_path: str
    azure_id: str
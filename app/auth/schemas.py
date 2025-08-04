from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    email: str
    username: str

class UserCreate(UserBase):
    password: str

class UserInDB(BaseModel):
    id: str
    hashed_password: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    created_at: Optional[datetime] = None

# Schemas para proyectos
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    azure_devops_token: str
    azure_org: str
    azure_project: str
    client_id: str
    client_secret: str

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    azure_devops_token: Optional[str] = None
    azure_org: Optional[str] = None
    azure_project: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    azure_org: str
    azure_project: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    active_project_id: Optional[str] = None

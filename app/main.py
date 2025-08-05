from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

# Importar rutas de autenticación
from .auth.routes import router as auth_router
from .auth.jwt import get_current_active_user, oauth2_scheme

# Importar rutas de la API
from .api.routes import (
    create_hu_endpoint,
    get_hus_endpoint, 
    get_hu_endpoint,
    generate_and_send_tests_endpoint,
    debug_list_hus_endpoint,
    debug_find_hu_endpoint,
    update_hu_status_endpoint,
    # Nuevas rutas de proyectos
    create_project_endpoint,
    get_user_projects_endpoint,
    set_active_project_endpoint,
    get_active_project_endpoint,
    # Nuevas rutas para editar y eliminar proyectos
    update_project_endpoint,
    delete_project_endpoint,
    # Nueva ruta para obtener HUs de un proyecto
    get_project_hus_endpoint,
    # Nueva ruta para eliminar HUs individuales
    delete_hu_endpoint,
    # Nueva ruta para validar contraseña
    validate_password_endpoint
)

from .schemas.hu_schemas import HUCreate, HUResponse, HUStatusUpdate, TestGenerationRequest, HUListResponse
from .auth.schemas import ProjectCreate, ProjectResponse, ProjectListResponse, ProjectUpdate
from .database.connection import get_db
from .database.models import User
from typing import List, Optional

# FastAPI app
app = FastAPI(title="RIWI QA Backend", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://qa-blackbird.diegormdev.site", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Incluir rutas de autenticación
app.include_router(auth_router)

# Endpoints públicos
@app.get("/")
async def root():
    return {"message": "RIWI QA Backend API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Endpoints protegidos
@app.post("/hus", response_model=HUResponse)
async def create_hu(
    hu_data: HUCreate, 
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return create_hu_endpoint(hu_data, current_user, db)



@app.get("/hus", response_model=HUListResponse)
async def get_hus(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db),
    status: str = None,
    name: str = None,
    azure_id: str = None,
    feature: str = None,
    module: str = None
):
    return get_hus_endpoint(db, status, name, azure_id, feature, module, current_user)

@app.get("/hus/{hu_id}", response_model=HUResponse)
async def get_hu(
    hu_id: str, 
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return get_hu_endpoint(hu_id, db)

@app.post("/generate-tests")
async def generate_and_send_tests(
    request: TestGenerationRequest, 
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return generate_and_send_tests_endpoint(request, current_user, db)

# Endpoints de depuración (requieren autenticación)
@app.get("/debug/hus")
async def debug_list_hus(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return debug_list_hus_endpoint(db)

@app.get("/debug/hu/{azure_id}")
async def debug_find_hu(
    azure_id: str, 
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return debug_find_hu_endpoint(azure_id, db)

@app.patch("/hus/{hu_id}/status", response_model=HUResponse)
async def update_hu_status(
    hu_id: str, 
    status_update: HUStatusUpdate, 
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return update_hu_status_endpoint(hu_id, status_update, current_user, db)

# ==================== ENDPOINTS DE GESTIÓN DE PROYECTOS ====================

@app.post("/projects", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return create_project_endpoint(project_data, current_user, db)

@app.get("/projects", response_model=ProjectListResponse)
async def get_user_projects(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return get_user_projects_endpoint(current_user, db)

@app.get("/projects/active", response_model=Optional[ProjectResponse])
async def get_active_project(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return get_active_project_endpoint(current_user, db)

@app.get("/projects/{project_id}/hus")
async def get_project_hus(
    project_id: str,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return get_project_hus_endpoint(project_id, current_user, db)

@app.delete("/hus/{hu_id}")
async def delete_hu(
    hu_id: str,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return delete_hu_endpoint(hu_id, current_user, db)

@app.post("/auth/validate-password")
async def validate_password(
    password_data: dict,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return validate_password_endpoint(password_data.get("password", ""), current_user, db)

@app.post("/projects/{project_id}/activate", response_model=ProjectResponse)
async def set_active_project(
    project_id: str,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return set_active_project_endpoint(project_id, current_user, db)

@app.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return update_project_endpoint(project_id, project_data, current_user, db)

@app.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    return delete_project_endpoint(project_id, current_user, db)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends

from .api.routes import (
    create_hu_endpoint, 
    get_hus_endpoint, 
    get_hu_endpoint,
    generate_and_send_tests_endpoint,
    debug_list_hus_endpoint,
    debug_find_hu_endpoint,
    update_hu_status_endpoint
)
from .schemas.hu_schemas import HUCreate, HUResponse, HUStatusUpdate, TestGenerationRequest
from .database.connection import get_db
from typing import List

# FastAPI app
app = FastAPI(title="RIWI QA Backend", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints
@app.get("/")
async def root():
    return {"message": "RIWI QA Backend API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/hus", response_model=HUResponse)
async def create_hu(hu_data: HUCreate, db = Depends(get_db)):
    return create_hu_endpoint(hu_data, db)

@app.get("/hus", response_model=List[HUResponse])
async def get_hus(
    db = Depends(get_db),
    status: str = None,
    name: str = None,
    azure_id: str = None,
    feature: str = None,
    module: str = None
):
    return get_hus_endpoint(db, status, name, azure_id, feature, module)

@app.get("/hus/{hu_id}", response_model=HUResponse)
async def get_hu(hu_id: str, db = Depends(get_db)):
    return get_hu_endpoint(hu_id, db)

@app.post("/generate-tests")
async def generate_and_send_tests(request: TestGenerationRequest, db = Depends(get_db)):
    return generate_and_send_tests_endpoint(request, db)

@app.get("/debug/hus")
async def debug_list_hus(db = Depends(get_db)):
    return debug_list_hus_endpoint(db)

@app.get("/debug/hu/{azure_id}")
async def debug_find_hu(azure_id: str, db = Depends(get_db)):
    return debug_find_hu_endpoint(azure_id, db)

@app.patch("/hus/{hu_id}/status", response_model=HUResponse)
async def update_hu_status(hu_id: str, status_update: HUStatusUpdate, db = Depends(get_db)):
    return update_hu_status_endpoint(hu_id, status_update, db)
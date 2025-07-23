from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from .schemas import Token, UserInDB, UserLogin
from .jwt import (
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_active_user
)
from ..database.connection import get_db
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}},
)

# Ruta para iniciar sesión y obtener token
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    print(f"\n=== Intento de inicio de sesión para el usuario: {form_data.username} ===")  # Debug
    
    # Autenticar al usuario
    user = authenticate_user(form_data.username, form_data.password)
    
    if not user:
        print(f"❌ Autenticación fallida para el usuario: {form_data.username}")  # Debug
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear token de acceso
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    print(f"✅ Usuario autenticado exitosamente: {user.username}")  # Debug
    return {"access_token": access_token, "token_type": "bearer"}

# Ruta protegida de ejemplo
@router.get("/me/")
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    return {"username": current_user.username, "email": current_user.email}

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .schemas import TokenData, UserInDB
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de seguridad
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3000

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Usuario de prueba (en producción, esto debería estar en una base de datos)
fake_users_db = {
    "test": {
        "username": "test",
        "email": "test@example.com",
        "password": "test123",  # Contraseña en texto plano SOLO para pruebas
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
}

def get_user(username: str) -> Optional[UserInDB]:
    """Obtiene un usuario de la base de datos ficticia"""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Autentica un usuario con nombre de usuario y contraseña"""
    print(f"Autenticando usuario: {username}")  # Debug
    user = get_user(username)
    if not user:
        print(f"Usuario no encontrado: {username}")  # Debug
        return None
    
    # Comparación directa de contraseñas (solo para pruebas)
    if password != user.password:
        print(f"Contraseña incorrecta para el usuario: {username}")  # Debug
        return None
        
    print(f"Usuario autenticado correctamente: {username}")  # Debug
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un token JWT con los datos proporcionados"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """Obtiene el usuario actual a partir del token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as e:
        print(f"Error al decodificar el token: {e}")  # Debug
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        print(f"Usuario no encontrado en la base de datos: {token_data.username}")  # Debug
        raise credentials_exception
        
    return user

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Verifica que el usuario esté activo"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user

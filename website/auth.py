from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import User, get_db
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt # python-jose
from passlib.context import CryptContext


# https://habr.com/ru/articles/340146/
# Secret key for JWT encryption
SECRET_KEY = "secretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 0.25

# Hashing algorithm for passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # bcrypt==4.0.1

# Function to hash passwords
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Function to verify a hashed password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Function to create a JWT access token
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

# Function to create a JWT access token for da chat
def create_chat_token(nickname: str, email: str, room_name: str):
    token_data = {"nickname": nickname, "email": email, "room_name": room_name}
    return create_access_token(data=token_data)

# Function to verify and decode JWT token
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(f"Authorization")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = token.split(" ")[1]  # Извлекаем только сам токен, убираем "Bearer"
    
    # Декодируем и проверяем токен
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            raise credentials_exception

        # Проверяем, истек ли токен
        if datetime.fromtimestamp(payload["exp"]) < datetime.now():
            # Удаляем куку
            response = RedirectResponse(url="/login/")
            response.delete_cookie(f"Authorization")
            return response

    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user

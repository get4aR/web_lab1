from fastapi import HTTPException, status
from jose import JWTError, jwt # python-jose

SECRET_KEY = "secretkey"
ALGORITHM = "HS256"

# Функция для получения nickname, email пользователя или названия чата из токена 
def get_current_user(token: str, user_type: str) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        nickname: str = payload.get("nickname")
        if nickname is None:
            raise credentials_exception

        email: str = payload.get("email")
        if email is None:
            raise credentials_exception

        chat: str = payload.get("room_name")
        if chat is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    # Вернуть необходимый тип
    match user_type:
        case "nickname":
            return nickname
        case "email":
            return email
        case "room_name":
            return chat
        case _:
            return None
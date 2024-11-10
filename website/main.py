from fastapi import FastAPI, Request, Response, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from auth import verify_password, get_password_hash, create_access_token, get_current_user, create_chat_token, ACCESS_TOKEN_EXPIRE_MINUTES
from schemas import ChatRoomCreate, Token, RoomRequest
from database import SessionLocal, engine, Base, get_db
from database import User, ChatRoom

# Создание таблиц БД
Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Начальная страница
@app.get("/")
def main_page(request: Request):
    return templates.TemplateResponse(request=request, name="main_page.html")

# Форма регистрации
@app.get("/reg/", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("reg.html", {"request": request})

# Регистрация
@app.post("/reg/")
def register(response: Response, nickname: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash the password and create the user
    hashed_password = get_password_hash(password)
    new_user = User(nickname=nickname, email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate JWT token -- РАЗОБРАТЬСЯ!!!
    access_token = create_access_token(data={"sub": new_user.email})

    response = RedirectResponse(url=f"/chatrooms/{new_user.id}", status_code=302)
    response.set_cookie(key=f"Authorization_{new_user.id}", value=f"Bearer {access_token}", httponly=True)

    return response

# Форма авторизации
@app.get("/login/", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Авторизация
@app.post("/login/")
def login(response: Response, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate JWT token for authentication
    access_token = create_access_token(data={"sub": user.email})

    response = RedirectResponse(url=f"/chatrooms/{user.id}", status_code=302)
    response.set_cookie(key=f"Authorization_{user.id}", value=f"Bearer {access_token}", httponly=True)

    return response

# Выход
@app.post("/logout/{user_id}/")
def logout(user_id: int, response: Response):
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key=f"Authorization_{user_id}")
    return response

# Форма чат-комнат
@app.get("/chatrooms/{user_id}/", response_class=HTMLResponse)
def get_chatrooms(user_id: int, request: Request, response: Response, db: Session = Depends(get_db)):
    user = get_current_user(user_id, request, db)

    # Если user -- это RedirectResponse, возвращаем его
    if isinstance(user, RedirectResponse):
        return user  # Перенаправляем на страницу логина

    chatrooms = db.query(ChatRoom).filter(ChatRoom.owner_id == user.id).order_by(ChatRoom.name).all()

    return templates.TemplateResponse("chatrooms.html", {
        "request": request,
        "user_chatrooms": chatrooms,
        "user": user
    })

# Создание чат-комнат
@app.post("/chatrooms/{user_id}/create/")
def create_chatroom(request: Request, create_name: str = Form(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db_chatroom = db.query(ChatRoom).filter(ChatRoom.name == create_name, ChatRoom.owner_id == user.id).first()
    if db_chatroom:
        raise HTTPException(status_code=400, detail=f"Chatroom with name {create_name} already exists")
    
    new_chatroom = ChatRoom(name=create_name, owner_id=user.id)
    db.add(new_chatroom)
    db.commit()
    db.refresh(new_chatroom)

    chatrooms = db.query(ChatRoom).filter(ChatRoom.owner_id == user.id).order_by(ChatRoom.name).all()

    return templates.TemplateResponse("chatrooms.html", {
        "request": request,
        "user_chatrooms": chatrooms,
        "user": user
    })

# Поиск чат-комнат
@app.get("/chatrooms/{user_id}/search/", response_class=HTMLResponse)
def search_chatrooms(request: Request, user_id: int, search_name: str, db: Session = Depends(get_db)):
    user = get_current_user(user_id, request, db)

    # Если user - это RedirectResponse, возвращаем его
    if isinstance(user, RedirectResponse):
        return user  # Перенаправляем на страницу логина
    
    chatrooms = db.query(ChatRoom).filter(ChatRoom.name.ilike(f"%{search_name}%")).order_by(ChatRoom.name).all()
    user = db.query(User).filter(User.id == user_id).first()
    
    # Получение всех комнат пользователя
    user_chatrooms = db.query(ChatRoom).filter(ChatRoom.owner_id == user.id).all()

    return templates.TemplateResponse("chatrooms.html", {
        "request": request,
        "chatrooms": chatrooms,  # Результаты поиска
        "user_chatrooms": user_chatrooms,  # Комнаты пользователя
        "user": user,
        "search_name": search_name  # Запрос поиска
    })

# Удаление чат-комнат
@app.post("/chatrooms/{user_id}/delete/{room_id}/")
def delete_chatrooms(request: Request, room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db_chatroom = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if db_chatroom is None:
        raise HTTPException(status_code=404, detail="Chatroom not found")
    
    if db_chatroom.owner_id != user.id:
        raise HTTPException(status_code=403, detail="U're NOT the owner of this chatroom")
    
    db.delete(db_chatroom)
    db.commit()

    chatrooms = db.query(ChatRoom).filter(ChatRoom.owner_id == user.id).order_by(ChatRoom.name).all()
    
    return templates.TemplateResponse("chatrooms.html", {
        "request": request,
        "user_chatrooms": chatrooms,
        "user": user
    })

# Создание токена для пользователя и комнаты
@app.post("/chatroom_token/{user_id}/", response_model=Token)
async def get_chat_token(request: RoomRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_chatroom = db.query(ChatRoom).filter(ChatRoom.name == request.room_name).first()
    if db_chatroom is None:
        raise HTTPException(status_code=404, detail="Chatroom not found")
    
    token = create_chat_token(user.nickname, user.email, request.room_name)

    return {"access_token": token, "token_type": "bearer"}
    # return redirect to chatroom

@app.get("/chatroom/{user_id}/", response_class=HTMLResponse)
def chatroom(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("chatroom.html", {"request": request})

from pydantic import BaseModel

# Создание комнаты
class ChatRoomCreate(BaseModel):
    name: str
    owner_id: int

# JWT
class Token(BaseModel):
    access_token: str
    token_type: str

# JWT for rooms
class RoomRequest(BaseModel):
    room_name: str

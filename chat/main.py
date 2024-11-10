from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Tuple
import json
from auth import get_current_user

app = FastAPI()

# Класс для управления WebSocket-соединениями и распределения сообщений по чатам
class ConnectionManager:
    def __init__(self):
        # Инициализируем список активных соединений в виде кортежей (WebSocket-соединение, название комнаты)
        self.active_connections: List[Tuple[WebSocket, str]] = []

    async def connect(self, websocket: WebSocket, room_name: str):
        # Принимаем WebSocket-соединение и добавляем его в список активных соединений с заданной комнатой
        await websocket.accept()
        self.active_connections.append((websocket, room_name))

    async def update(self, websocket: WebSocket, new_chat: str):
        # Обновляем название комнаты для указанного WebSocket-соединения, если оно существует в списке
        for index, (connection, chat) in enumerate(self.active_connections):
            if connection == websocket:
                # Заменяем комнату для найденного соединения на новую
                self.active_connections[index] = (connection, new_chat)
                break

    def disconnect(self, websocket: WebSocket):
        # Удаляем WebSocket-соединение из списка активных соединений
        # Исключаем только соединения, не совпадающие с переданным WebSocket
        self.active_connections = [
            connection for connection in self.active_connections if connection[0] != websocket
        ]

    async def send_message(self, room_name: str, message: str, msg_type: str, username: str = ""):
        # Отправляем сообщение в указанный чат (room_name) всем соединениям, принадлежащим этой комнате
        # Формируем данные для сообщения, включая тип, текст и, если указано, имя пользователя
        data = {
            "type": msg_type,       # Тип сообщения: "system" для системных или "user" для пользовательских сообщений
            "message": message,     # Основное текстовое содержание сообщения
            "username": username    # Имя отправителя (для системных сообщений оставляется пустым)
        }
        for connection, chat in self.active_connections:
            if chat == room_name:
                # Отправляем JSON-данные как текстовое сообщение в WebSocket
                await connection.send_text(json.dumps(data))


manager = ConnectionManager()

# Маршрут для обработки WebSocket соединения
@app.websocket("/ws/chatroom/")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket, "")

    nickname = ""
    chat = ""
    email = ""
    try:
        while True:
            data = await websocket.receive_text()

            message_data = json.loads(data)

            # Соединение...
            if message_data["type"] == "onOpen":
                # nickname, email и имя chatroom'a из JWT
                nickname = get_current_user(message_data["token"], "nickname")
                email = get_current_user(message_data["token"], "email")
                chat = get_current_user(message_data["token"], "room_name")

                # Сообщение о подключении
                if nickname and email and chat:
                    await manager.update(websocket, chat)
                    await manager.send_message(chat, f"{nickname} подключился к {chat}", "system")

            # Сообщение от пользователя
            elif message_data["type"] == "userMsg":
                message = message_data["message"]
                await manager.send_message(chat, message, "user", nickname)

    # Отключение пользователя
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.send_message(chat, f"{nickname} покинул {chat}", "system")
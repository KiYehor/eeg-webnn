from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path
from pydantic import BaseModel
import os
import numpy as np

app = FastAPI()

# Указываем абсолютный путь к фронтенду
BASE_DIR = Path(__file__).parent.parent  # Поднимаемся на уровень выше (в eeg-web-app)
FRONTEND_DIR = BASE_DIR / "frontend" / "public"

print(f"Frontend path: {FRONTEND_DIR}")
print(f"Files in frontend: {os.listdir(FRONTEND_DIR)}")

# Раздаем статические файлы
app.mount("/static", StaticFiles(directory="frontend/public"), name="static")

class User(BaseModel):
    username: str
    password: str

@app.post("/register")
async def register(request: Request):
    data = await request.json()  # Получаем JSON-данные из запроса
    if not data or "username" not in data or "password" not in data:
        return jsonify({"message": "Ошибка: укажите username и password"}), 400

    username = data["username"]
    password = data["password"]

    # Пример: сохраняем пользователя в файл (в будущем можно заменить на базу данных)
    with open("users.txt", "a") as f:
        f.write(f"{username}:{password}\n")

@app.get("/register", response_class=HTMLResponse)
async def serve_frontend():
    register_path = FRONTEND_DIR / "register.html" 
    with open(register_path, encoding="utf-8") as file:
        return file.read()

@app.get("/login", response_class=HTMLResponse)
async def serve_login():
    login_path = FRONTEND_DIR / "login.html"
    with open(login_path, encoding="utf-8") as file:
        return file.read()

@app.get("/api/eeg")
def get_eeg():
    return {"data": [0.1, -0.2, 0.3]}

# Разрешаем запросы от фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)
#генерация говна для теста
@app.get("/api\generate-eeg")
def generate_eeg():
    t = np.linspace(0, 5, 1000)  # 5 секунд, 1000 точек
    signal = np.sin(2 * np.pi * 10 * t) + 0.2 * np.random.normal(size=t.shape)  # Альфа-ритм + шум
    return {"time": t.tolist(), "signal": signal.tolist()}

# аунтефикация, не работает
fake_users_db = {
    "admin": {"password": "admin123"},
    "user1": {"password": "password1"}
}
#логин нерабочий, но изолированный
@app.post("/login")
async def login(username: str, password: str):
    if username not in fake_users_db:
        raise HTTPException(status_code=400, detail="User not found")
    
    if fake_users_db[username]["password"] != password:
        raise HTTPException(status_code=400, detail="Wrong password")
    
    return {"message": "Login successful"}


# Запуск: uvicorn app:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    input("Нажмите Enter для выхода...")  # Окно не закроется, пока не нажмёшь Enter
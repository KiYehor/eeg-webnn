from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from pathlib import Path
from pydantic import BaseModel
from datetime import datetime
import bcrypt
import json
import os
import uuid
import numpy as np

app = FastAPI()

FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "public"
HISTORY_DIR = Path("history")
HISTORY_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class EEGResult(BaseModel):
    timestamp: str
    result: str
    focus: float
    relax: float
class User(BaseModel):
    username: str
    password: str

@app.get("/export/pdf/{username}")
async def export_history_pdf(username: str):
    filepath = HISTORY_DIR / f"{username}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="History not found")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            history = json.load(f)

        if not history:
            raise HTTPException(status_code=400, detail="History is empty")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"EEG Analysis History for User: {username}", styles["Title"]))
        elements.append(Spacer(1, 12))

        for i, session in enumerate(history):
            start = session.get("start", "N/A")
            end = session.get("end", "N/A")
            elements.append(Paragraph(f"<b>Session {i+1}</b> (From: {start} To: {end})", styles["Heading2"]))
            elements.append(Spacer(1, 6))

            entries = session.get("entries", [])
            if isinstance(entries, list):
                for j, entry in enumerate(entries):
                    text = (
                        f"{j+1}. Timestamp: {entry.get('timestamp', '---')}<br/>"
                        f"Result: {entry.get('result', '---')}, "
                        f"Focus: {entry.get('focus', '---')}, Relax: {entry.get('relax', '---')}<br/><br/>"
                    )
                    elements.append(Paragraph(text, styles["Normal"]))
            else:
                elements.append(Paragraph("⚠ Nieprawidłowy format danych sesji.", styles["Italic"]))

            elements.append(Spacer(1, 12))

        doc.build(elements)
        buffer.seek(0)

        headers = {
            "Content-Disposition": f"attachment; filename={username}_eeg_history.pdf"
        }
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)

    except Exception as e:
        print(f"[PDF EXPORT ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
    
@app.get("/visualization", response_class=HTMLResponse)
async def serve_visualization():
    path = FRONTEND_DIR / "visualization.html"
    with open(path, encoding="utf-8") as file:
        return file.read()

@app.post("/register")
async def register(request: Request):
    data = await request.json()  # Получаем JSON-данные из запроса
    if not data or "username" not in data or "password" not in data:
        return {"message": "Error: укажите username и password"}, 400

    username = data["username"]
    password = data["password"]
    users_db = load_users()
    if username in users_db:
        raise HTTPException(status_code=400, detail="The user already exists")     
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    with open("users.txt", "a", encoding="utf-8") as f:
        f.write(f"{username}:{hashed_pw}\n")

    return {"message": "Registration was successful."}

# Функция для чтения пользователей из файла (заменить когда будет база данных)
def load_users():
    users = {}
    if os.path.exists("users.txt"):
        with open("users.txt", "r") as file:
            for line in file:
                if ":" in line:
                    username, password = line.strip().split(":")
                    users[username] = {"password": password}
    return users

@app.post("/login")
async def login(request: Request):
    data = await request.json()
    username = data["username"]
    password = data["password"]
    users_db = load_users()  
    if username not in users_db:
        return {"message": "Wrong password or username"} 
    stored_hashed_pw = users_db[username]["password"]
    if not bcrypt.checkpw(password.encode("utf-8"), stored_hashed_pw.encode("utf-8")):
        return {"message": "Wrong password or username"}

    return {"message": "Login successful"}
    

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

@app.get("/eeg", response_class=HTMLResponse)
async def serve_frontend():
    register_path = FRONTEND_DIR / "eeg.html" 
    with open(register_path, encoding="utf-8") as file:
        return file.read()

@app.post("/save_result")
async def save_result(request: Request):
    data = await request.json()
    username = data.get("username", "anonymous")
    result = data.get("result")
    focus = data.get("focus")
    relax = data.get("relax")
    timestamp = datetime.now().isoformat()

    with open("eeg_history.txt", "a", encoding="utf-8") as f:
        f.write(f"{username},{timestamp},{result},{focus},{relax}\n")

    return {"message": "Result saved"}
@app.get("/history", response_class=HTMLResponse)
async def serve_history():
    path = FRONTEND_DIR / "history.html"
    with open(path, encoding="utf-8") as file:
        return file.read()

@app.post("/history/{username}")
async def save_history(username: str, request: Request):
    try:
        session_entries = await request.json()
        if not isinstance(session_entries, list):
            raise ValueError("A list of records was expected (list)")
    except Exception as e:
        return {"error": f"Invalid JSON: {str(e)}"}
    filepath = HISTORY_DIR / f"{username}.json"
    history = []
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
                if not isinstance(history, list):
                    history = []
            except json.JSONDecodeError:
                history = []
    # Получение начала и конца сессии
    start_time = session_entries[0].get("timestamp") if session_entries else datetime.now().isoformat()
    end_time = session_entries[-1].get("timestamp") if session_entries else start_time
    new_session = {
        "session_id": str(uuid.uuid4()),
        "start": start_time,
        "end": end_time,
        "entries": session_entries  # гарантированно список
    }
    history.append(new_session)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    return {"status": "ok"}

@app.get("/history/{username}")
async def get_history(username: str):
    filepath = HISTORY_DIR / f"{username}.json"
    if not filepath.exists():
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        history = json.load(f)

    return history

# Разрешаем запросы от фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)
# WebSocket для реального времени
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        # Здесь можно добавить предобработку данных для WebNN
        await websocket.send_json({"status": "processed", "data": data})

@app.post("/process")
async def process_data(request: Request):
    data = await request.json()
    # Обычная HTTP-обработка (если нужно)
    return {"result": "Data received"}


# Запуск: uvicorn app:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    input("Нажмите Enter для выхода...")  # Окно не закроется, пока не нажмёшь Enter
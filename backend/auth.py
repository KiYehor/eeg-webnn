from fastapi import FastAPI, HTTPException

app = FastAPI()

# ????????? "?????????" ????????????? (?????? ??)
fake_users_db = {
    "admin": {"password": "admin123"},
    "user1": {"password": "password1"}
}

@app.post("/login")
async def login(username: str, password: str):
    if username not in fake_users_db:
        raise HTTPException(status_code=400, detail="User not found")
    
    if fake_users_db[username]["password"] != password:
        raise HTTPException(status_code=400, detail="Wrong password")
    
    return {"message": "Login successful"}

@app.post("/register")
async def register(username: str, password: str):
    if username in fake_users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    
    fake_users_db[username] = {"password": password}
    return {"message": "User created"}
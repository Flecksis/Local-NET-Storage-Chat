from fastapi import FastAPI, Request, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import json
import os
import uuid
from typing import Optional
from pathlib import Path
import shutil
from datetime import datetime
import uvicorn
from passlib.context import CryptContext

app = FastAPI(title="NowDrop")

# Сессии
app.add_middleware(
    SessionMiddleware,
    secret_key="404-52-key-52-404",
    max_age=3600,
)

# хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

templates = Jinja2Templates(directory="templates")

Path("data").mkdir(exist_ok=True)
Path("storage/common").mkdir(exist_ok=True, parents=True)
Path("storage/users").mkdir(exist_ok=True, parents=True)
Path("data/logs").mkdir(exist_ok=True, parents=True)

def init_data_files():
    users_file = Path("data/users.json")
    chat_file = Path("data/chat.json")
    logs_file = Path("data/logs.json")

    if not users_file.exists():
        with open(users_file, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "username": "admin",
                    "password": pwd_context.hash("admin123"),
                    "name": "Администратор",
                    "admin": True
                },
                {
                    "username": "user1",
                    "password": pwd_context.hash("password1"),
                    "name": "Пользователь 1",
                    "admin": False
                }
            ], f, ensure_ascii=False)

    if not chat_file.exists():
        with open(chat_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)

    if not logs_file.exists():
        with open(logs_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)

init_data_files()

def log_action(username: str, action: str, details: str):
    logs_file = Path("data/logs.json")
    with open(logs_file, "r", encoding="utf-8") as f:
        logs = json.load(f)
    logs.append({
        "id": str(uuid.uuid4()),
        "username": username,
        "action": action,
        "details": details,
        "timestamp": str(datetime.now())
    })
    with open(logs_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

# Проверка авт
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Вход не выполнен")
    return user

# Проверка адм прав
def get_admin_user(request: Request):
    user = get_current_user(request)
    if not user.get("admin", False):
        raise HTTPException(status_code=403, detail="Аксес денай сори")
    return user

# Ручки
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)): #динамик тайпс давай гуляй тоже да
    try:
        with open("data/users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
        for user in users:
            if user["username"] == username and pwd_context.verify(password, user["password"]):
                request.session["user"] = user
                log_action(username, "login", "User logged in")
                return RedirectResponse(url="/dashboard", status_code=303)
        raise HTTPException(status_code=401, detail="Пермишинс динай")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        user = get_current_user(request)
        return templates.TemplateResponse("index.html", {"request": request, "user": user})
    except Exception:
        return RedirectResponse(url="/")

@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, admin: dict = Depends(get_admin_user)):
    try:
        with open("data/users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
        return templates.TemplateResponse("admin.html", {"request": request, "users": users, "admin": admin})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading : {str(e)}")

@app.get("/log", response_class=HTMLResponse)
async def log_page(request: Request, admin: dict = Depends(get_admin_user)):
    try:
        with open("data/logs.json", "r", encoding="utf-8") as f:
            logs = json.load(f)
        return templates.TemplateResponse("log.html", {"request": request, "logs": logs, "admin": admin})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading : {str(e)}")

@app.get("/api/users")
async def get_users(admin: dict = Depends(get_admin_user)):
    try:
        with open("data/users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения юзера: {str(e)}")

@app.post("/api/users")
async def create_user(request: Request, username: str = Form(...), password: str = Form(...), name: str = Form(...), admin: bool = Form(False), current_user: dict = Depends(get_admin_user)):
    try:
        with open("data/users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
        if any(user["username"] == username for user in users):
            raise HTTPException(status_code=400, detail="Имя пользователя уже существует")
        new_user = {
            "username": username,
            "password": pwd_context.hash(password),
            "name": name,
            "admin": admin
        }
        users.append(new_user)
        with open("data/users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        log_action(current_user["username"], "create_user", f"Создан юзер {username}")
        return {"message": "Юзер успешно создан"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания юзера: {str(e)}")

@app.put("/api/users/{username}")
async def update_user(username: str, request: Request, name: str = Form(...), password: Optional[str] = Form(None), admin: bool = Form(False), current_user: dict = Depends(get_admin_user)):
    try:
        with open("data/users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
        for user in users:
            if user["username"] == username:
                user["name"] = name
                user["admin"] = admin
                if password:
                    user["password"] = pwd_context.hash(password)
                break
        else:
            raise HTTPException(status_code=404, detail="Юзер не найден")
        with open("data/users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        log_action(current_user["username"], "update_user", f"Обновлён юзер {username}")
        return {"message": "Обновлён юзер успешно "}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не обновлён юзер  ошибка: {str(e)}")

@app.delete("/api/users/{username}")
async def delete_user(username: str, current_user: dict = Depends(get_admin_user)):
    try:
        with open("data/users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
        users = [user for user in users if user["username"] != username]
        with open("data/users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        user_folder = Path(f"storage/users/user_{username}")
        if user_folder.exists():
            shutil.rmtree(user_folder)
        log_action(current_user["username"], "delete_user", f"Удалён юзер {username}")
        return {"message": "Юзер успешно удалён"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления юзера: {str(e)}")

@app.get("/api/users/{username}/files")
async def get_user_files(username: str, current_user: dict = Depends(get_admin_user)):
    try:
        user_folder = Path(f"storage/users/user_{username}")
        if not user_folder.exists():
            return []
        files = []
        folders = []
        for item in user_folder.iterdir():
            if item.is_file():
                files.append({
                    "name": item.name,
                    "size": item.stat().st_size,
                    "modified": item.stat().st_mtime,
                    "type": "file"
                })
            elif item.is_dir():
                folders.append({
                    "name": item.name,
                    "size": 0,
                    "modified": item.stat().st_mtime,
                    "type": "folder"
                })
        return folders + files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения файлов юзера: {str(e)}")

# Чатикс
@app.get("/api/chat")
async def get_chat():
    try:
        with open("data/chat.json", "r", encoding="utf-8") as f:
            messages = json.load(f)
        return messages
    except:
        return []

@app.post("/api/chat")
async def send_message(request: Request, message: str = Form(...)):
    try:
        user = get_current_user(request)
        with open("data/chat.json", "r", encoding="utf-8") as f:
            messages = json.load(f)
        new_message = {
            "id": str(uuid.uuid4()),
            "username": user["username"],
            "name": user["name"],
            "message": message,
            "timestamp": str(datetime.now())
        }
        messages.append(new_message)
        with open("data/chat.json", "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        log_action(user["username"], "send_message", f"Отправлено сообщение: {message}")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки сообщения : {str(e)}")

# Файлы
@app.get("/api/files/{category}")
async def get_files(category: str, request: Request, path: Optional[str] = None):
    try:
        user = get_current_user(request)
        if category == "common":
            base_path = Path("storage/common")
        elif category == "personal":
            user_folder = f"user_{user['username']}"
            base_path = Path(f"storage/users/{user_folder}")
            base_path.mkdir(exist_ok=True)
        else:
            raise HTTPException(status_code=400, detail="Неверная категория ")
        if path:
            full_path = base_path / path
            if not full_path.exists() or not full_path.is_dir():
                raise HTTPException(status_code=404, detail="Папка не найдена")
        else:
            full_path = base_path
        files = []
        folders = []
        for item in full_path.iterdir():
            if item.is_file():
                files.append({
                    "name": item.name,
                    "size": item.stat().st_size,
                    "modified": item.stat().st_mtime,
                    "type": "file"
                })
            elif item.is_dir():
                folders.append({
                    "name": item.name,
                    "size": 0,
                    "modified": item.stat().st_mtime,
                    "type": "folder"
                })
        log_action(user["username"], "list_files", f"Перечисленные файлы в {category}/{path or ''}")
        return folders + files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файлов: {str(e)}")

@app.post("/api/upload/{category}")
async def upload_file(category: str, request: Request, file: UploadFile = File(...), path: Optional[str] = None):
    try:
        user = get_current_user(request)
        if category == "common":
            base_path = Path("storage/common")
        elif category == "personal":
            user_folder = f"user_{user['username']}"
            base_path = Path(f"storage/users/{user_folder}")
            base_path.mkdir(exist_ok=True)
        else:
            raise HTTPException(status_code=400, detail="Неверная категория")
        if path:
            upload_path = base_path / path
            upload_path.mkdir(exist_ok=True, parents=True)
        else:
            upload_path = base_path
        file_path = upload_path / file.filename
        if file_path.exists():
            name_parts = file.filename.rsplit('.', 1)
            if len(name_parts) > 1:
                base_name, extension = name_parts
                counter = 1
                while file_path.exists():
                    new_filename = f"{base_name}_{counter}.{extension}"
                    file_path = upload_path / new_filename
                    counter += 1
            else:
                counter = 1
                while file_path.exists():
                    new_filename = f"{file.filename}_{counter}"
                    file_path = upload_path / new_filename
                    counter += 1
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        log_action(user["username"], "upload_file", f"Загружено {file_path.name} в {category}/{path or ''}")
        return {"status": "success", "filename": file_path.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {str(e)}")

@app.delete("/api/files/{category}/{filename}")
async def delete_file(category: str, filename: str, request: Request, path: Optional[str] = None):
    try:
        user = get_current_user(request)
        if category == "common":
            base_path = Path("storage/common")
        elif category == "personal":
            user_folder = f"user_{user['username']}"
            base_path = Path(f"storage/users/{user_folder}")
        else:
            raise HTTPException(status_code=400, detail="Неверная категория")
        if path:
            file_path = base_path / path / filename
        else:
            file_path = base_path / filename
        if file_path.exists():
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                shutil.rmtree(file_path)
            log_action(user["username"], "delete_file", f"Удалён {filename} в {category}/{path or ''}")
            return {"status": "success"}
        else:
            raise HTTPException(status_code=404, detail="Файл не найден")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления файла: {str(e)}")

@app.get("/api/download/{category}/{filename}")
async def download_file(category: str, filename: str, request: Request, path: Optional[str] = None):
    try:
        user = get_current_user(request)
        if category == "common":
            base_path = Path("storage/common")
        elif category == "personal":
            user_folder = f"user_{user['username']}"
            base_path = Path(f"storage/users/{user_folder}")
        else:
            raise HTTPException(status_code=400, detail="Неверная категория")
        if path:
            file_path = base_path / path / filename
        else:
            file_path = base_path / filename
        if file_path.exists():
            log_action(user["username"], "download_file", f"Скачен {filename} из {category}/{path or ''}")
            return FileResponse(file_path, filename=filename)
        else:
            raise HTTPException(status_code=404, detail="Файл не найден ")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {str(e)}")

@app.post("/api/rename/{category}")
async def rename_file(category: str, request: Request):
    try:
        user = get_current_user(request)
        data = await request.json()
        old_name = data.get("oldName")
        new_name = data.get("newName")
        path = data.get("path")
        if not old_name or not new_name:
            raise HTTPException(status_code=400, detail="Отсутствующие имена файлов")
        if category == "common":
            base_path = Path("storage/common")
        elif category == "personal":
            user_folder = f"user_{user['username']}"
            base_path = Path(f"storage/users/{user_folder}")
        else:
            raise HTTPException(status_code=400, detail="Неверная категория")
        if path:
            old_path = base_path / path / old_name
            new_path = base_path / path / new_name
        else:
            old_path = base_path / old_name
            new_path = base_path / new_name
        if not old_path.exists():
            raise HTTPException(status_code=404, detail="Файл не найден")
        if new_path.exists():
            raise HTTPException(status_code=400, detail="Файл с таким именем уже существует")
        old_path.rename(new_path)
        log_action(user["username"], "rename_file", f"Переименован файл {old_name} в {new_name} в {category}/{path or ''}")
        return {"message": "Файл успешно переименован"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка переименования: {str(e)}")

@app.post("/api/folder/{category}")
async def create_folder(category: str, request: Request):
    try:
        user = get_current_user(request)
        data = await request.json()
        folder_name = data.get("folderName")
        path = data.get("path")
        if not folder_name:
            raise HTTPException(status_code=400, detail="Отсутствующее имя папки")
        if category == "common":
            base_path = Path("storage/common")
        elif category == "personal":
            user_folder = f"user_{user['username']}"
            base_path = Path(f"storage/users/{user_folder}")
        else:
            raise HTTPException(status_code=400, detail="Неверная папка ")
        if path:
            folder_path = base_path / path / folder_name
        else:
            folder_path = base_path / folder_name
        if folder_path.exists():
            raise HTTPException(status_code=400, detail="Папка уже существует")
        folder_path.mkdir(exist_ok=True, parents=True)
        log_action(user["username"], "create_folder", f"Создана папка {folder_name} в {category}/{path or ''}")
        return {"message": "Успешно создана папка"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания папки: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)#http://127.0.0.1:8000/
from __future__ import annotations
import uuid
import logging
import threading
import os
import urllib.parse
from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import secrets
from starlette.middleware.sessions import SessionMiddleware

from src.drivers.selenium_driver import SeleniumDriver
from src.config.settings import Settings

app = FastAPI()

templates = Jinja2Templates(directory="src/webapp/templates")

os.makedirs("src/webapp/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="src/webapp/static"), name="static")

app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))

logger = logging.getLogger(__name__)

settings = Settings()

SITE_PASSWORD = os.environ.get("SITE_PASSWORD", settings.app_config.log_level if hasattr(settings.app_config, 'password') else "admin123")

class ParsingForm(BaseModel):
    company_name: str
    company_site: str
    source: str
    email: str
    output_filename: str = "report.csv"
    search_scope: str = "country"
    location: str = ""
    proxy_server: Optional[str] = ""

    @classmethod
    async def as_form(cls, request: Request):
        form_data = await request.form()
        try:
            return cls(**form_data)
        except Exception as e:
            logger.error(f"Error parsing form data: {e}", exc_info=True)
            raise HTTPException(status_code=422, detail=f"Error processing form data: {e}")

def check_auth(request: Request) -> bool:
    return request.session.get("authenticated", False)

@app.get("/login")
async def login_page(request: Request):
    if check_auth(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == SITE_PASSWORD:
        request.session["authenticated"] = True
        return RedirectResponse(url="/", status_code=302)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный пароль"})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

@app.get("/")
async def read_root(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request, "error": None, "success": None})

active_tasks: Dict[str, Dict[str, Any]] = {}

class TaskStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@app.post("/start_parsing")
async def start_parsing(request: Request, form_data: ParsingForm = Depends(ParsingForm.as_form)):
    if not check_auth(request):
        return RedirectResponse(url="/login", status_code=302)
    
    task_id = str(uuid.uuid4())
    
    active_tasks[task_id] = {
        "task_id": task_id,
        "status": TaskStatus.PENDING,
        "progress": "Инициализация...",
        "email": form_data.email,
        "source": form_data.source,
        "result_file": None,
        "error": None,
        "timestamp": str(uuid.uuid4())
    }
    
    def run_parsing():
        try:
            active_tasks[task_id]["status"] = TaskStatus.RUNNING
            active_tasks[task_id]["progress"] = "Запуск парсинга..."
            
            driver = SeleniumDriver(settings=settings)
            driver.start()
            
            active_tasks[task_id]["progress"] = "Парсинг завершен (минимальная версия)"
            active_tasks[task_id]["status"] = TaskStatus.COMPLETED
            
            driver.stop()
        except Exception as e:
            logger.error(f"Error in parsing task {task_id}: {e}", exc_info=True)
            active_tasks[task_id]["status"] = TaskStatus.FAILED
            active_tasks[task_id]["error"] = str(e)
    
    thread = threading.Thread(target=run_parsing, daemon=True)
    thread.start()
    
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=302)

@app.get("/tasks/{task_id}")
async def get_task(request: Request, task_id: str):
    if not check_auth(request):
        return RedirectResponse(url="/login", status_code=302)
    
    if task_id not in active_tasks:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    task = active_tasks[task_id]
    return templates.TemplateResponse("task_status.html", {"request": request, "task": task})

@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    if task_id not in active_tasks:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    return JSONResponse(active_tasks[task_id])

@app.get("/tasks")
async def get_all_tasks():
    tasks_list = list(active_tasks.values())
    return {"tasks": tasks_list}


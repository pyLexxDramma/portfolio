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
from src.parsers.yandex_parser import YandexParser
from src.parsers.gis_parser import GisParser
from src.storage.csv_writer import CSVWriter
from src.utils.task_manager import TaskStatus, active_tasks, create_task, update_task_status
from src.config.settings import Settings

app = FastAPI()

templates = Jinja2Templates(directory="src/webapp/templates")

os.makedirs("src/webapp/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="src/webapp/static"), name="static")

app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))

logger = logging.getLogger(__name__)

settings = Settings()

SITE_PASSWORD = os.environ.get("SITE_PASSWORD", "admin123")
if hasattr(settings.app_config, 'password') and settings.app_config.password:
    SITE_PASSWORD = settings.app_config.password

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

def _generate_yandex_url(company_name: str, search_scope: str, location: str) -> str:
    encoded_company_name = urllib.parse.quote(company_name)
    if search_scope == "city" and location:
        encoded_location = urllib.parse.quote(location)
        if location.lower() == "москва":
            return f"https://yandex.ru/maps/?text={encoded_company_name}%2C+{encoded_location}&ll=37.617300%2C55.755826&z=12"
        elif location.lower() == "санкт-петербург":
            return f"https://yandex.ru/maps/?text={encoded_company_name}%2C+{encoded_location}&ll=30.315868%2C59.939095&z=11"
        else:
            return f"https://yandex.ru/maps/?text={encoded_company_name}%2C+{encoded_location}"
    else:
        search_text = location if location else "Россия"
        full_search_text = f"{search_text}%20{encoded_company_name}"
        return f"https://yandex.ru/maps/?text={full_search_text}&mode=search&z=3"

def _generate_gis_url(company_name: str, company_site: str, search_scope: str, location: str) -> str:
    encoded_company_name = urllib.parse.quote(company_name, safe='')
    encoded_company_site = urllib.parse.quote(company_site, safe='')
    if search_scope == "city" and location:
        encoded_location = urllib.parse.quote(location, safe='')
        return f"https://2gis.ru/{encoded_location}/search/{encoded_company_name}?search_source=main&company_website={encoded_company_site}"
    else:
        return f"https://2gis.ru/search/{encoded_company_name}?search_source=main&company_website={encoded_company_site}"

def _run_parser_task(parser_class, url: str, task_id: str, source: str):
    driver = None
    try:
        update_task_status(task_id, TaskStatus.RUNNING, "Инициализация драйвера...")
        driver = SeleniumDriver(settings=settings)
        driver.start()
        
        update_task_status(task_id, TaskStatus.RUNNING, f"Запуск парсера {source}...")
        parser = parser_class(driver=driver, settings=settings)
        
        def update_progress(msg: str):
            update_task_status(task_id, TaskStatus.RUNNING, f"{source}: {msg}")
        
        parser.set_progress_callback(update_progress)
        
        result = parser.parse(url=url)
        
        update_task_status(task_id, TaskStatus.RUNNING, f"Парсинг {source} завершен")
        return result, None
    except Exception as e:
        logger.error(f"Error in parser task {task_id} ({source}): {e}", exc_info=True)
        return None, str(e)
    finally:
        if driver:
            try:
                driver.stop()
            except:
                pass

@app.post("/start_parsing")
async def start_parsing(request: Request, form_data: ParsingForm = Depends(ParsingForm.as_form)):
    if not check_auth(request):
        return RedirectResponse(url="/login", status_code=302)
    
    if not form_data.company_name or not form_data.company_site or not form_data.source or not form_data.email:
        return RedirectResponse(url="/?error=Missing+required+fields", status_code=302)
    
    task_id = create_task(
        email=form_data.email,
        source_info={
            'company_name': form_data.company_name,
            'company_site': form_data.company_site,
            'source': form_data.source,
            'search_scope': form_data.search_scope,
            'location': form_data.location
        }
    )
    
    def run_parsing():
        try:
            if form_data.source == 'both':
                update_task_status(task_id, TaskStatus.RUNNING, "Запуск парсинга обоих источников...")
                
                yandex_url = _generate_yandex_url(form_data.company_name, form_data.search_scope, form_data.location)
                gis_url = _generate_gis_url(form_data.company_name, form_data.company_site, form_data.search_scope, form_data.location)
                
                yandex_result, yandex_error = _run_parser_task(YandexParser, yandex_url, task_id, "Yandex")
                gis_result, gis_error = _run_parser_task(GisParser, gis_url, task_id, "2GIS")
                
                all_cards = []
                if yandex_result:
                    cards = yandex_result.get('cards_data', [])
                    for card in cards:
                        card['source'] = 'yandex'
                    all_cards.extend(cards)
                if gis_result:
                    cards = gis_result.get('cards_data', [])
                    for card in cards:
                        card['source'] = '2gis'
                    all_cards.extend(cards)
                
                if all_cards:
                    writer = CSVWriter(settings=settings)
                    results_dir = settings.app_config.writer.output_dir
                    os.makedirs(results_dir, exist_ok=True)
                    output_path = os.path.join(results_dir, form_data.output_filename)
                    writer.set_file_path(output_path)
                    
                    with writer:
                        for card in all_cards:
                            writer.write(card)
                    
                    task = active_tasks[task_id]
                    task.result_file = form_data.output_filename
                    task.detailed_results = all_cards
                
                if yandex_error or gis_error:
                    update_task_status(task_id, TaskStatus.COMPLETED, f"Завершено с ошибками: Yandex={bool(yandex_error)}, 2GIS={bool(gis_error)}")
                else:
                    update_task_status(task_id, TaskStatus.COMPLETED, f"Парсинг завершен. Найдено карточек: {len(all_cards)}")
            elif form_data.source == 'yandex':
                url = _generate_yandex_url(form_data.company_name, form_data.search_scope, form_data.location)
                result, error = _run_parser_task(YandexParser, url, task_id, "Yandex")
                
                if error:
                    update_task_status(task_id, TaskStatus.FAILED, f"Ошибка: {error}", error=error)
                elif result and result.get('cards_data'):
                    writer = CSVWriter(settings=settings)
                    results_dir = settings.app_config.writer.output_dir
                    os.makedirs(results_dir, exist_ok=True)
                    writer.set_file_path(os.path.join(results_dir, form_data.output_filename))
                    
                    with writer:
                        for card in result['cards_data']:
                            writer.write(card)
                    
                    task = active_tasks[task_id]
                    task.result_file = form_data.output_filename
                    task.detailed_results = result['cards_data']
                    update_task_status(task_id, TaskStatus.COMPLETED, f"Парсинг завершен. Найдено карточек: {len(result['cards_data'])}")
                else:
                    update_task_status(task_id, TaskStatus.COMPLETED, "Парсинг завершен. Карточки не найдены")
            elif form_data.source == '2gis':
                url = _generate_gis_url(form_data.company_name, form_data.company_site, form_data.search_scope, form_data.location)
                result, error = _run_parser_task(GisParser, url, task_id, "2GIS")
                
                if error:
                    update_task_status(task_id, TaskStatus.FAILED, f"Ошибка: {error}", error=error)
                elif result and result.get('cards_data'):
                    writer = CSVWriter(settings=settings)
                    results_dir = settings.app_config.writer.output_dir
                    os.makedirs(results_dir, exist_ok=True)
                    writer.set_file_path(os.path.join(results_dir, form_data.output_filename))
                    
                    with writer:
                        for card in result['cards_data']:
                            writer.write(card)
                    
                    task = active_tasks[task_id]
                    task.result_file = form_data.output_filename
                    task.detailed_results = result['cards_data']
                    update_task_status(task_id, TaskStatus.COMPLETED, f"Парсинг завершен. Найдено карточек: {len(result['cards_data'])}")
                else:
                    update_task_status(task_id, TaskStatus.COMPLETED, "Парсинг завершен. Карточки не найдены")
        except Exception as e:
            logger.error(f"Error in parsing task {task_id}: {e}", exc_info=True)
            update_task_status(task_id, TaskStatus.FAILED, f"Критическая ошибка: {str(e)}", error=str(e))
    
    thread = threading.Thread(target=run_parsing, daemon=True)
    thread.start()
    
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=302)

@app.get("/tasks/{task_id}")
async def get_task(request: Request, task_id: str):
    if not check_auth(request):
        return RedirectResponse(url="/login", status_code=302)
    
    task = active_tasks.get(task_id)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    task_dict = {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "email": task.email,
        "source_info": task.source_info,
        "result_file": task.result_file,
        "error": task.error,
        "timestamp": str(task.timestamp),
        "statistics": task.statistics,
        "detailed_results": task.detailed_results
    }
    return templates.TemplateResponse("task_status.html", {"request": request, "task": task_dict})

@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    task = active_tasks.get(task_id)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    task_dict = {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "email": task.email,
        "source_info": task.source_info,
        "result_file": task.result_file,
        "error": task.error,
        "timestamp": str(task.timestamp),
        "statistics": task.statistics
    }
    return JSONResponse(task_dict)

@app.get("/tasks")
async def get_all_tasks():
    tasks_list = []
    for task in active_tasks.values():
        task_dict = {
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress,
            "email": task.email,
            "source_info": task.source_info,
            "result_file": task.result_file,
            "error": task.error,
            "timestamp": str(task.timestamp)
        }
        tasks_list.append(task_dict)
    return {"tasks": tasks_list}


import sys
import os

os.environ['PYTHONUNBUFFERED'] = '1'

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')
    except:
        pass

if __name__ == "__main__":
    import uvicorn
    import logging
    
    # Настраиваем uvicorn для вывода логов в реальном времени
    # Отключаем стандартное логирование uvicorn, чтобы использовать наше
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.setLevel(logging.INFO)
    
    uvicorn.run(
        "src.webapp.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True,
        use_colors=False,  # Отключаем цвета для лучшей совместимости
        log_config=None  # Используем настройки логирования из settings.py
    )



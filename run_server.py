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

    uvicorn.run(
        "src.webapp.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )


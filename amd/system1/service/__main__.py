"""`python -m service` (run from amd/system1/, or /app in the image): serve on $HOST:$PORT (default 0.0.0.0:8082)."""
import uvicorn

from .config import Settings

if __name__ == "__main__":
    s = Settings.from_env()
    uvicorn.run("service.app:app", host=s.host, port=s.port, workers=1, log_level="info")

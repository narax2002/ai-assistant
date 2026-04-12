import logging
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import load_settings
from interfaces.api_server import create_api_app
from services.shared import create_app_context

STATIC_DIR = Path(__file__).parent / "static"

LOGGER = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    settings = load_settings()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    LOGGER.info("Starting LLM Gateway API server")

    ctx = create_app_context(settings)
    app = create_api_app(ctx)

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

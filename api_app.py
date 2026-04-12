import logging

import uvicorn
from dotenv import load_dotenv

from config import load_settings
from interfaces.api_server import create_api_app
from services.shared import create_app_context

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

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

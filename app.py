import logging

import discord
from dotenv import load_dotenv

from config import load_settings
from interfaces.discord_bot import create_research_bot
from runtime_lock import single_instance_lock

LOGGER = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    settings = load_settings()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    LOGGER.info("Starting research assistant")

    client = create_research_bot(settings)

    try:
        with single_instance_lock():
            client.run(settings.discord_bot_token)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    except discord.LoginFailure as exc:
        raise SystemExit("Discord rejected DISCORD_BOT_TOKEN.") from exc


if __name__ == "__main__":
    main()

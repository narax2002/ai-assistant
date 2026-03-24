import logging

import discord
from dotenv import load_dotenv

from bot.discord_bot import create_bot
from config import load_settings
from runtime_lock import single_instance_lock


def main() -> None:
    load_dotenv()
    settings = load_settings()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bot = create_bot(settings)

    try:
        with single_instance_lock():
            bot.run(settings.discord_bot_token)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    except discord.PrivilegedIntentsRequired as exc:
        raise SystemExit(
            "Enable Message Content Intent in the Discord Developer Portal to use the current !ask command."
        ) from exc
    except discord.LoginFailure as exc:
        raise SystemExit("Discord rejected DISCORD_BOT_TOKEN.") from exc


if __name__ == "__main__":
    main()

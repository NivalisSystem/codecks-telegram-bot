import asyncio
import logging
import termcolor
from bot import Bot
from dotenv import load_dotenv


def start():
    """
    Entry point of the program.
    """
    logging.info(termcolor.colored("Starting bot...", "green"))
    bot: Bot = Bot()

    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(bot.start())
    else:
        asyncio.run(bot.start())


if __name__ == "__main__":
    logging_level: int = logging.INFO

    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s - %(levelname)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    load_dotenv()

    start()

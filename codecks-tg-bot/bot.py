import asyncio
import logging
import os
import termcolor

from codecks import Codecks
from telegram_helpers import Telegram
from telegram.ext import ApplicationBuilder

PROCCESS_NAME = "codecks-tg-bot"


class Bot:

    app: ApplicationBuilder
    codecks: Codecks
    TELEGRAM_BOT_TOKEN: str
    telegram: Telegram

    def __init__(self):
        self.stay_alive: bool = True
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    async def start(self) -> None:
        logging.info(termcolor.colored(f"Starting {PROCCESS_NAME}", "green"))

        logging.info(termcolor.colored("Starting local codecks integrations", "blue"))
        self.codecks = Codecks()
        await self.codecks.async_init()

        logging.info(termcolor.colored("Building tg application", "blue"))

        self.app = ApplicationBuilder().token(self.TELEGRAM_BOT_TOKEN).build()
        self.telegram = Telegram(self.app, self.codecks.codecks, self.shutdown)
        await self.telegram.add_handlers()

        logging.info(termcolor.colored("Initialising tg application", "blue"))
        await self.app.initialize()

        try:
            logging.info(termcolor.colored("Starting tg application", "blue"))
            await self.app.start()

            logging.info(
                termcolor.colored("App started!\nStarting polling...", "green")
            )
            await self.app.updater.start_polling()

            while self.stay_alive:
                await asyncio.sleep(1)
        finally:
            logging.info(termcolor.colored("Stopping tg application", "blue"))
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

            logging.info(termcolor.colored("Application stopped!", "green"))

    async def shutdown(self) -> None:
        self.stay_alive = False

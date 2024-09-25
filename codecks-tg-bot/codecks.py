import asyncio
import logging
import termcolor


from codecks_data import CodecksData

BACKGROUND_PROCESS_INTERVAL = 60  # in seconds


class Codecks:
    def __init__(self):
        self.codecks = CodecksData()
        self.shutdown = False

    async def async_init(self):
        await self.codecks.load_project()
        # start a loop to check for updates every x minutes
        asyncio.create_task(self.check_for_activity_process())

    async def check_for_activity_process(self) -> None:
        """
        Checks for new activities and updates the project data if necessary.
        """

        logging.info(termcolor.colored("Starting background check proccess", "green"))

        while not self.shutdown:
            logging.info(
                termcolor.colored("Checking for activity since last update", "blue")
            )
            await self.codecks.get_history_data()

            await asyncio.sleep(BACKGROUND_PROCESS_INTERVAL)

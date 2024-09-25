import asyncio
import datetime
import importlib
import json
import logging
import os
import re
import requests
import sys
import termcolor

from codecks_api import CodecksAPI

CODECKS_DATA_DIR = "data"
DATE_REGEX = r"\[\d{2}/\d{2}/\d{2}\]"


class CodecksData:
    def __init__(self):
        self.data: dict = {}
        self.data_lock: asyncio.Lock = asyncio.Lock()
        self.last_update: datetime.datetime = datetime.datetime(1970, 1, 1)
        self.last_update_lock: asyncio.Lock = asyncio.Lock()
        self.api = CodecksAPI()
        self.data_dir = os.path.join(CODECKS_DATA_DIR, self.api.CODECKS_SUBDOMAIN)
        self.data_filepath = os.path.join(self.data_dir, "codecks.json")

    async def load_project(self) -> None:
        """
        loads the project data from local storage or from Codecks if it is not available
        """
        if not os.path.exists(self.data_filepath):
            await self.get_project_data()

        try:
            with open(self.data_filepath, "r", encoding="utf-8") as file:
                self.data = json.load(file)

            async with self.last_update_lock:
                self.last_update = datetime.datetime.strptime(
                    self.data.get("last_update"), "%Y-%m-%dT%H:%M:%SZ"
                )
        except Exception as e:
            logging.error(
                termcolor.colored(
                    f"Failed to load project data from local storage: {e}", "red"
                )
            )

    async def save_project(self) -> None:
        """
        saves the project data to local storage"""
        async with self.last_update_lock:
            last_updated = self.last_update

        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)

        # add the last update time to the data
        self.data["last_update"] = last_updated

        try:
            with open(self.data_filepath, "w", encoding="utf-8") as file:
                json.dump(self.data, file)
        except Exception as e:
            logging.error(
                termcolor.colored(
                    f"Failed to save project data to local storage: {e}", "red"
                )
            )

    async def get_project_data(self) -> None:
        async with self.last_update_lock:
            self.last_update = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        response: dict = await self.api.fetch_project()

        if response:
            logging.info(
                "Saving project data to local storage from Codecks, updated at %s",
                self.last_update,
            )
            async with self.data_lock:
                self.data = response
                await self.save_project()
        else:
            logging.error(
                termcolor.colored(
                    "Failed to fetch project data from Codecks API", "red"
                )
            )

    async def get_card_data(self, card_ids: list[str]) -> None:
        response: dict = await self.api.fetch_cards(card_ids)

        if response:
            logging.info("Fetched card data from Codecks API")
            async with self.data_lock:
                # TODO: need to check if the card data response matches the expected format
                self.data.update(response)
                self.save_project()
        else:
            logging.error(
                termcolor.colored("Failed to fetch card data from Codecks API", "red")
            )

    async def get_history_data(self) -> None:
        async with self.last_update_lock:
            last_update_time: datetime.datetime = self.last_update

        response: dict = await self.api.fetch_history(last_update_time)

        if response:
            # update the last update time
            async with self.last_update_lock:
                self.last_update = datetime.datetime.now(
                    datetime.timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")

            logging.info("Fetched history data from Codecks API")
            activity_data = response.get("activity", [])
            logging.info(
                termcolor.colored("%d activities fetched", "green"), len(activity_data)
            )

            if len(activity_data) > 0:
                card_ids = [activity["card"] for activity in activity_data]
                await self.get_card_data(card_ids)

    async def get_decks(self) -> list[dict]:
        async with self.data_lock:
            return self.data.get("deck", [])

    async def get_cards(self, deck_id: str = "") -> list[dict]:
        decks = None
        cards = None

        async with self.data_lock:
            cards = self.data.get("card", {})
            decks = self.data.get("deck", {})

        if not isinstance(cards, dict) or not isinstance(decks, dict):
            logging.error(
                termcolor.colored("Failed to fetch cards from project data", "red")
            )
            return []

        matching_decks = [
            deck_info.get("id")
            for deck_info in decks.values()
            if deck_id.lower() in deck_info.get("title", "").lower()
        ]

        matching_cards = [
            card_info
            for card_info in cards.values()
            if card_info.get("deckId") in matching_decks
        ]

        return matching_cards

    async def get_card_info(self, card_id: str) -> dict:
        async with self.data_lock:
            return self.data.get("card", {}).get(card_id, {})

    async def get_due_cards(self, days_ahead: int = 30) -> list[dict]:
        cards = None
        decks = None

        async with self.data_lock:
            cards = self.data.get("card", {})
            decks = self.data.get("deck", {})

        cards_with_due_dates = [
            {"card": card, "matches": re.findall(DATE_REGEX, card.get("content", ""))}
            for card in cards.values()
            if re.search(DATE_REGEX, card.get("content", ""))
        ]

        cards_with_due_dates.sort(
            key=lambda x: datetime.datetime.strptime(x["matches"][0], "[%d/%m/%y]")
        )

        if days_ahead > 0:
            cards_with_due_dates = [
                card
                for card in cards_with_due_dates
                if datetime.datetime.strptime(card["matches"][0], "[%d/%m/%y]")
                <= datetime.datetime.now() + datetime.timedelta(days=days_ahead)
            ]

        return cards_with_due_dates

    def create_card(self, project_id, card_data):
        # TODO: implement this function to create a new card in Codecks
        pass

    def update_card(self, card_id, updated_data):
        # TODO: implement this function to update an existing card in Codecks
        pass

    def delete_card(self, card_id):
        # TODO: implement this function to delete a card from Codecks
        pass

    def add_due_date_to_card(self, card_id, due_date):
        # TODO: implement this function to add a due date to a card in Codecks
        # we probably just want to make this a function of updating a cards info
        pass

    # Add more data-related functions as needed

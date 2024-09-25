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

CODECKS_API_URL = "https://api.codecks.io/"


class CodecksAPI:
    """
    Class that defines the API requests to Codecks."""

    CODECKS_API_TOKEN: str
    CODECKS_SUBDOMAIN: str

    def __init__(self):
        self.CODECKS_API_TOKEN = os.getenv("CODECKS_API_TOKEN")
        self.CODECKS_SUBDOMAIN = os.getenv("CODECKS_SUBDOMAIN")
        if not self.CODECKS_API_TOKEN:
            raise ValueError("CODECKS_API_TOKEN is not set.")
        if not self.CODECKS_SUBDOMAIN:
            raise ValueError("CODECKS_SUBDOMAIN is not set.")

    async def fetch_project(self) -> dict:
        """
        Fetches all of the project data."""
        data = {}
        data["query"] = {
            "_root": [
                {
                    "account": [
                        "name",
                        {
                            "decks": [
                                "id",
                                "title",
                                "project",
                                {"cards": ["title", "content"]},
                            ],
                        },
                    ]
                }
            ]
        }

        return await self.make_request(data=data)

    async def fetch_history(self, last_update_time: datetime.datetime) -> dict:
        """
        Fetches all activities that have been created after the given time."""
        data = {}
        data["query"] = {
            "_root": [
                {
                    "account": [
                        {
                            f'activities({{"createdAt": {{"op": "gt", "value": "{last_update_time}"}}}})': [
                                "card",
                                "createdAt",
                                "changer",
                            ]
                        }
                    ]
                }
            ]
        }

        return await self.make_request(data=data)

    async def fetch_cards(self, cards: list[str]) -> dict:
        """
        Fetches cards that match the given list of card IDs."""
        data = {}
        data["query"] = {
            "_root": [
                {
                    "account": [
                        {
                            "cards": [
                                {"id": {"op": "in", "value": cards}},
                                "title",
                                "content",
                            ]
                        }
                    ]
                }
            ]
        }
        return await self.make_request(data=data)

    async def make_request(self, method: str = "POST", data: dict = None) -> dict:
        headers = {
            "X-Account": self.CODECKS_SUBDOMAIN,
            "X-Auth-Token": self.CODECKS_API_TOKEN,
            "Content-Type": "application/json",
        }

        logging.info(
            termcolor.colored(f"API request to {CODECKS_API_URL}:\n{data}", "blue")
        )

        try:
            return self.handle_response(
                response=requests.request(
                    method, CODECKS_API_URL, headers=headers, json=data, timeout=10
                )
            )

        except requests.exceptions.Timeout as e:
            logging.warning(termcolor.colored(f"Timeout error: {e}", "yellow"))
        except requests.exceptions.RequestException as e:
            logging.error(termcolor.colored(f"Request error: {e}", "red"))
        except Exception as e:
            logging.error(termcolor.colored(f"Unhandled exception caught: {e}", "red"))

        return None

    def handle_response(self, response: requests.Response) -> None:
        logging.debug(termcolor.colored(f"API response:\n{response}", "blue"))

        # successful response
        if response.status_code == 200:
            logging.info(termcolor.colored("API request successful.", "green"))
            return response.json()

        # bad request
        if response.status_code == 400:
            logging.error(
                termcolor.colored(
                    "Bad request. Please check your request parameters.", "red"
                )
            )

        # unauthorized
        elif response.status_code == 401:

            logging.error(
                termcolor.colored("Unauthorized. Please check your API token.", "red")
            )

        # not found
        elif response.status_code == 404:

            logging.error(termcolor.colored("Resource not found.", "red"))

        # internal server error
        elif response.status_code == 500:
            logging.error(termcolor.colored("Internal server error.", "red"))

        # timeout
        elif response.status_code == 408:
            logging.warning(termcolor.colored("Request timed out.", "yellow"))

        # catch all other codes
        else:
            logging.error(
                termcolor.colored(
                    f"Unexpected status code: {response.status_code}", "red"
                )
            )

        return None

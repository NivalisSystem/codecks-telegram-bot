import logging
import os
import termcolor

from codecks_data import CodecksData
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)


class Telegram:
    app: ApplicationBuilder
    authorised_users: list[int]
    codecks: CodecksData

    def __init__(
        self,
        app: ApplicationBuilder,
        codecks_data: CodecksData,
        shutdown_callback: callable,
    ):
        self.app = app
        self.authorised_users = [
            int(user_id) for user_id in os.getenv("ALLOWED_USERS").split(",")
        ]
        self.shutdown_callback: callable = shutdown_callback
        self.codecks = codecks_data

    async def add_handlers(self) -> None:
        """
        Adds the handlers to the telegram bot
        """
        logging.info(termcolor.colored("Adding handlers to the telegram bot", "blue"))

        # Group 0: Handle all messages (including commands)
        self.app.add_handler(MessageHandler(filters.ALL, self.handle_message), group=0)

        # Group 1: Handle all commands
        # Generic commands
        self.app.add_handler(CommandHandler("help", self.help), group=1)
        self.app.add_handler(CommandHandler("mew", self.mew), group=1)
        self.app.add_handler(CommandHandler("start", self.start), group=1)

        # bot control commands
        self.app.add_handler(CommandHandler("stop", self.stop), group=1)
        # self.app.add_handler(CommandHandler("test", self.test), group=1)
        # self.app.add_handler(CommandHandler("reload", self.reload), group=1)

        # codecks commands
        self.app.add_handler(CommandHandler("cards", self.list_cards), group=1)
        self.app.add_handler(CommandHandler("cardinfo", self.card_info), group=1)
        self.app.add_handler(CommandHandler("decks", self.list_decks), group=1)
        self.app.add_handler(
            CommandHandler("upcoming", self.upcoming_due_dates), group=1
        )

        # Callback query handler
        self.app.add_handler(CallbackQueryHandler(self.handle_callback_query), group=1)

    def user_authorised(self, user_id: int) -> bool:
        """
        Return true if the user is in the authorised users list"""
        return user_id in self.authorised_users

    async def check_permissions(self, update: Update, context) -> bool:
        """
        Checks if the user is authorised to use the bot"""
        user_id = update.effective_user.id
        if not self.user_authorised(user_id):
            await self.reply_to(
                update, context, "You are not authorised to use this bot."
            )
            logging.error(
                termcolor.colored(
                    "An unauthorised user tried to use this service!", "red"
                )
            )
            logging.error(termcolor.colored(f"User: {update.effective_user}", "red"))
            return False
        return True

    async def reply_to(
        self, update: Update, _context, reply, markup=None, parse_mode=None
    ) -> None:
        """
        Used to reply to a user with a message"""
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=reply, reply_markup=markup, parse_mode=parse_mode
            )
        else:
            await update.message.reply_text(
                reply, reply_markup=markup, parse_mode=parse_mode
            )

    # --------------------- HANDLERS ----------------

    async def handle_message(self, update: Update, context) -> None:
        """
        Used to log who is accesing the bot"""
        # TODO: perhaps actually save this to a file? or at least in a seperate logging stream
        logging.info(
            termcolor.colored(
                f"Received message from user: {update.effective_user}", "green"
            )
        )

    async def handle_callback_query(self, update: Update, context) -> None:
        logging.info(
            termcolor.colored(
                f"Received message from user: {update.effective_user}", "green"
            )
        )
        if not await self.check_permissions(update, context):
            return

        query = update.callback_query
        await query.answer()

        command = query.data
        if not context.args:
            context.args = []

        context.args.extend(command.split()[1:])

        if command.startswith("/cards"):
            await self.list_cards(update, context)
        elif command.startswith("/cardinfo"):
            await self.card_info(update, context)
        elif command.startswith("/decks"):
            await self.list_decks(update, context)

    # --------------------- COMMANDS ----------------
    # Generic commands

    async def help(self, update: Update, context) -> None:
        if not await self.check_permissions(update, context):
            return  # If unauthorized, stop here
        await self.reply_to(update, context, "I'm not very helpful yet, sorry :c")

    async def mew(self, update: Update, context) -> None:
        if not await self.check_permissions(update, context):
            return  # If unauthorized, stop here

        await self.reply_to(
            update, context, "mememewwwww, love you so much liomns 💟💜🟪"
        )

    async def start(self, update: Update, context) -> None:
        await self.list_decks(update, context)

    # bot control commands

    async def stop(self, update: Update, context) -> None:
        if not await self.check_permissions(update, context):
            return  # If unauthorized, stop here
        await update.message.reply_text("Shutting down...")

        self.shutdown_callback()

    # codecks commands
    async def list_cards(self, update: Update, context) -> None:
        if not await self.check_permissions(update, context):
            return  # If unauthorized, stop here

        logging.info(termcolor.colored("Fetching cards", "blue"))
        deck = context.args[0] if context.args else ""

        cards = await self.codecks.get_cards(deck)

        buttons = [
            [
                InlineKeyboardButton(
                    f"{card_info.get('title', 'Err: No Title')}",
                    callback_data=f"/cardinfo {card_info.get('cardId', '')} {deck}",
                )
            ]
            for card_info in cards
        ]

        buttons.append(
            [InlineKeyboardButton("[Return to decks]", callback_data="/decks")]
        )
        await self.reply_to(
            update,
            context,
            f"Cards for: {deck}",
            markup=InlineKeyboardMarkup(buttons),
        )

    async def list_decks(self, update: Update, context) -> None:
        if not await self.check_permissions(update, context):
            return  # If unauthorized, stop here

        logging.info(termcolor.colored("Fetching decks", "blue"))

        decks = await self.codecks.get_decks()
        buttons = [
            [
                InlineKeyboardButton(
                    deck_info.get("title", "No Title"),
                    callback_data=f"/cards {deck_info.get('title', '')}",
                )
            ]
            for deck_info in decks.values()
        ]

        await self.reply_to(
            update, context, "Decks:", markup=InlineKeyboardMarkup(buttons)
        )

    async def card_info(self, update: Update, context) -> None:
        if not await self.check_permissions(update, context):
            return  # If unauthorized, stop here

        logging.info(termcolor.colored("Fetching card info", "blue"))
        cardID = None
        deck = None

        if context.args and len(context.args) >= 1:
            cardID = context.args[0] if context.args else None
            if len(context.args) > 1:
                deck = context.args[1]

        if not cardID:
            logging.warning(termcolor.colored("No card ID provided", "yellow"))
            await self.reply_to(update, context, "No card ID provided")
            return

        card = await self.codecks.get_card_info(cardID)
        card_info = (
            f"<b>{card.get('title', 'No Title')}</b>\n\n"
            f"<pre>{card.get('content', 'No Content')}</pre>\n\n"
        )

        buttons = []
        if deck:
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"[Return to {deck}]", callback_data=f"/cards {deck}"
                    )
                ]
            )
        else:
            buttons.append(
                [InlineKeyboardButton("[Return to decks]", callback_data="/decks")]
            )

        await self.reply_to(
            update,
            context,
            card_info,
            parse_mode="HTML",
            markup=InlineKeyboardMarkup(buttons),
        )

    async def upcoming_due_dates(self, update: Update, context) -> None:
        if not await self.check_permissions(update, context):
            return  # If unauthorized, stop here

        logging.info(termcolor.colored("Fetching upcoming due dates", "blue"))

        days_to_check: int = 30
        if context.args:
            try:
                days_to_check = int(context.args[0])
            except ValueError as e:
                logging.error(termcolor.colored(f"Invalid argument: {e}", "red"))
                await self.reply_to(update, context, "Invalid argument")
                return

        cards = await self.codecks.get_due_cards(days_to_check)
        decks = await self.codecks.get_decks()

        for card in cards:
            card_info = card.get("card")
            date = card.get("matches")[0]
            deck = decks.get(card_info.get("deckId", ""), {}).get(
                "title", "Unknown Deck"
            )
            text = (
                f"<b>{deck}: {card_info.get('title', 'No Title')}</b>\n"
                f"<pre>{card_info.get('content', 'No Content')}</pre>\n"
                f"Due: {date}"
            )
            await self.reply_to(update, context, text, parse_mode="HTML")

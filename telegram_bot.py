import asyncio
import logging
import threading

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token, chat_id, get_latest_temp):
        self.chat_id = chat_id
        self.get_latest_temp = get_latest_temp  # callable returning float or None
        self.app = Application.builder().token(token).build()
        self.app.add_handler(CommandHandler("temp", self._temp))
        self.app.add_handler(CommandHandler("start", self._temp))

    def _authorized(self, update: Update) -> bool:
        return update.effective_chat.id == self.chat_id

    async def _temp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._authorized(update):
            logger.warning("Ignored message from chat %s", update.effective_chat.id)
            return
        temp = self.get_latest_temp()
        text = "No reading yet." if temp is None else f"Current temp: {temp:.1f}°F"
        await update.message.reply_text(text)

    def start(self):
        """Run the bot in a background thread so the main loop keeps going."""
        def run():
            asyncio.set_event_loop(asyncio.new_event_loop())
            self.app.run_polling(stop_signals=None)  # signals only work in the main thread

        threading.Thread(target=run, daemon=True, name="telegram").start()
        logger.info("Telegram bot started")
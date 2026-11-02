import os
import logging
import asyncio
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from dotenv import load_dotenv
from handlers import register_handlers

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

async def error_handler(error, body):
    logging.error(f"Error: {error} - {body}")

app.error(error_handler)


register_handlers(app)

async def main():
    logging.info("Starting kagent Slack bot")
    app_handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await app_handler.start_async()

if __name__ == "__main__":
    asyncio.run(main())
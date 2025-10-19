import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from flyerapi import Flyer

from .config import Settings, load_settings
from .database import db
from .handlers import register_handlers
from .middlewares import ThrottlingMiddleware


async def on_startup(bot: Bot) -> None:
    logging.info("Bot started as %s", (await bot.get_me()).username)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings: Settings = load_settings()

    await db.setup()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    flyer_client = Flyer(settings.flyer_api_key) if settings.flyer_api_key else None
    dp.workflow_data.update(settings=settings, flyer=flyer_client)

    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.5))

    register_handlers(dp)

    dp.startup.register(on_startup)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

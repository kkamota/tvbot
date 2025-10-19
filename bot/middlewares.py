import asyncio
from collections import defaultdict
from typing import Any, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 1.0) -> None:
        super().__init__()
        self.rate_limit = rate_limit
        self._user_timestamps: Dict[int, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        async with self._lock:
            now = asyncio.get_running_loop().time()
            last_time = self._user_timestamps[user.id]
            if now - last_time < self.rate_limit:
                return
            self._user_timestamps[user.id] = now
        return await handler(event, data)


def mask_sensitive(text: str) -> str:
    if len(text) <= 6:
        return "*" * len(text)
    return text[:3] + "*" * (len(text) - 6) + text[-3:]

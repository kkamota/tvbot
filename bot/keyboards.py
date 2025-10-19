from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="🎁 Ежедневный бонус")],
            [KeyboardButton(text="👥 Реферальная ссылка"), KeyboardButton(text="🏆 Топ приглашений")],
            [KeyboardButton(text="💳 Вывод средств"), KeyboardButton(text="✅ Проверить подписку")],
        ],
        resize_keyboard=True,
    )


def subscribe_keyboard(channel_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Перейти в канал", url=f"https://t.me/{channel_username.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")],
        ]
    )


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📜 Запросы на вывод", callback_data="admin_withdrawals")],
            [InlineKeyboardButton(text="🔐 Перегенерировать защитный PIN", callback_data="admin_regen_pin")],
        ]
    )


def withdrawal_actions_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выплачено", callback_data=f"withdraw_paid:{request_id}"),
                InlineKeyboardButton(text="❌ Отклонено", callback_data=f"withdraw_rejected:{request_id}"),
            ]
        ]
    )

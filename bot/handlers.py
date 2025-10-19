from __future__ import annotations

import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .config import Settings
from .database import User, db
from .keyboards import (
    admin_menu_keyboard,
    main_menu_keyboard,
    subscribe_keyboard,
    withdrawal_actions_keyboard,
)
from .middlewares import mask_sensitive

router = Router()


class WithdrawStates(StatesGroup):
    waiting_for_amount = State()


async def ensure_user(message: Message, settings: Settings) -> User:
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    if user is None:
        await db.create_user(telegram_id, settings.start_bonus, None)
        user = await db.get_user(telegram_id)
    return user  # type: ignore[return-value]


@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject, bot: Bot, settings: Settings) -> None:
    telegram_id = message.from_user.id
    args = command.args or ""
    referred_by: Optional[int] = None
    if args.startswith("ref") and args[3:].isdigit():
        referred_by = int(args[3:])
        if referred_by == telegram_id:
            referred_by = None

    user = await db.get_user(telegram_id)
    if user is None:
        await db.create_user(telegram_id, settings.start_bonus, referred_by)
        user = await db.get_user(telegram_id)
        await message.answer(
            "Добро пожаловать! На ваш баланс начислено 3 ⭐ за регистрацию.",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await message.answer("С возвращением!", reply_markup=main_menu_keyboard())

    if referred_by and user and user.referred_by is None:
        await db.assign_referrer(telegram_id, referred_by)

    bot_info = await bot.get_me()
    await message.answer(
        "Поделитесь ботом с друзьями и зарабатывайте звезды!",
        reply_markup=subscribe_keyboard(settings.channel_username),
    )
    await message.answer(
        "Ваша персональная ссылка: https://t.me/{username}?start=ref{tg_id}".format(
            username=bot_info.username,
            tg_id=telegram_id,
        )
    )


@router.message(F.text == "💰 Баланс")
async def show_balance(message: Message, settings: Settings) -> None:
    user = await ensure_user(message, settings)
    await message.answer(f"На вашем балансе {user.balance} ⭐")


@router.message(F.text == "🎁 Ежедневный бонус")
async def daily_bonus(message: Message, settings: Settings) -> None:
    user = await ensure_user(message, settings)
    now = datetime.datetime.utcnow()
    last_bonus = None
    if user.last_daily_bonus:
        last_bonus = datetime.datetime.fromisoformat(user.last_daily_bonus)

    if last_bonus and (now - last_bonus) < datetime.timedelta(hours=24):
        remaining = datetime.timedelta(hours=24) - (now - last_bonus)
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes = remainder // 60
        await message.answer(
            f"Следующий бонус будет доступен через {hours} ч {minutes} мин."
        )
        return

    await db.update_balance(user.telegram_id, settings.daily_bonus)
    await db.set_last_daily_bonus(user.telegram_id, now.isoformat())
    await message.answer(
        f"Вы получили {settings.daily_bonus} ⭐ ежедневного бонуса!"
    )


@router.message(F.text == "👥 Реферальная ссылка")
async def referral_link(message: Message, bot: Bot, settings: Settings) -> None:
    user = await ensure_user(message, settings)
    bot_info = await bot.get_me()
    await message.answer(
        "Поделитесь этой ссылкой: https://t.me/{username}?start=ref{tg_id}".format(
            username=bot_info.username,
            tg_id=user.telegram_id,
        )
    )


@router.message(F.text == "🏆 Топ приглашений")
async def top_referrers(message: Message, settings: Settings) -> None:
    await ensure_user(message, settings)
    top = await db.list_top_referrers()
    if not top:
        await message.answer("Пока нет приглашений. Будьте первым!")
        return
    lines = ["Топ приглашений:"]
    for index, (telegram_id, total) in enumerate(top, start=1):
        masked = mask_sensitive(str(telegram_id))
        lines.append(f"{index}. {masked} — {total} друзей")
    await message.answer("\n".join(lines))


@router.message(F.text == "✅ Проверить подписку")
async def check_subscription(message: Message, bot: Bot, settings: Settings) -> None:
    user = await ensure_user(message, settings)
    member = await bot.get_chat_member(settings.channel_username, message.from_user.id)
    if member.status not in {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    }:
        await message.answer(
            "Пожалуйста, подпишитесь на канал, чтобы получать награды.",
            reply_markup=subscribe_keyboard(settings.channel_username),
        )
        return

    if not user.is_subscribed:
        await db.set_subscription(user.telegram_id, True)
        await message.answer("Спасибо за подписку! Награды активированы.")
    else:
        await message.answer("Подписка уже подтверждена.")

    if user.referred_by and not user.reward_claimed:
        await db.update_balance(user.referred_by, settings.referral_bonus)
        await db.mark_reward_claimed(user.telegram_id)
        await message.answer("Вашему другу начислено 3 ⭐ за приглашение!")


@router.message(F.text == "💳 Вывод средств")
async def withdrawal_request(message: Message, settings: Settings, state: FSMContext) -> None:
    user = await ensure_user(message, settings)
    if user.balance < settings.min_withdrawal:
        await message.answer(
            f"Минимальная сумма вывода {settings.min_withdrawal} ⭐. На вашем балансе {user.balance} ⭐."
        )
        return
    await state.set_state(WithdrawStates.waiting_for_amount)
    await message.answer(
        "Введите сумму для вывода (не менее {minimum} ⭐):".format(
            minimum=settings.min_withdrawal
        )
    )


@router.message(WithdrawStates.waiting_for_amount)
async def process_withdraw_amount(message: Message, settings: Settings, state: FSMContext) -> None:
    user = await ensure_user(message, settings)
    try:
        amount = int(message.text)
    except (TypeError, ValueError):
        await message.answer("Введите целое число.")
        return

    if amount < settings.min_withdrawal:
        await message.answer(
            f"Минимальная сумма вывода {settings.min_withdrawal} ⭐. Попробуйте снова."
        )
        return

    if amount > user.balance:
        await message.answer("Недостаточно средств для вывода.")
        return

    await db.update_balance(user.telegram_id, -amount)
    await db.add_withdrawal(user.telegram_id, amount)
    await state.clear()
    await message.answer(
        "Заявка на вывод создана. Администратор свяжется с вами в ближайшее время."
    )


@router.message(Command("admin"))
async def admin_panel(message: Message, settings: Settings) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    if message.from_user.id not in settings.admin_ids:
        await message.answer("Доступ запрещен.")
        return
    await message.answer("Админ-панель", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, settings: Settings) -> None:
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    total_users = await db.count_users()
    total_balance = await db.sum_balances()
    await callback.message.edit_text(
        f"Всего пользователей: {total_users}\n"
        f"Общий баланс: {total_balance} ⭐",
        reply_markup=admin_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_withdrawals")
async def admin_withdrawals(callback: CallbackQuery, settings: Settings) -> None:
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    requests = await db.list_withdrawals(status="pending")
    if not requests:
        await callback.answer("Нет ожидающих заявок", show_alert=True)
        return
    for request in requests:
        await callback.message.answer(
            f"Заявка #{request.id}\nПользователь: {request.telegram_id}\nСумма: {request.amount} ⭐\nСоздана: {request.created_at}",
            reply_markup=withdrawal_actions_keyboard(request.id),
        )
    await callback.answer()


async def _update_withdrawal_status(callback: CallbackQuery, status: str) -> None:
    _, raw_id = callback.data.split(":", 1)
    request_id = int(raw_id)
    await db.set_withdrawal_status(request_id, status)
    await callback.message.edit_text(
        callback.message.text + f"\nСтатус обновлен: {status}",
    )
    await callback.answer("Статус обновлен")


@router.callback_query(F.data.startswith("withdraw_paid"))
async def withdrawal_paid(callback: CallbackQuery, settings: Settings) -> None:
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    await _update_withdrawal_status(callback, "paid")


@router.callback_query(F.data.startswith("withdraw_rejected"))
async def withdrawal_rejected(callback: CallbackQuery, settings: Settings) -> None:
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    await _update_withdrawal_status(callback, "rejected")


@router.callback_query(F.data == "admin_regen_pin")
async def regen_pin(callback: CallbackQuery, settings: Settings) -> None:
    import secrets

    new_pin = secrets.token_hex(3)
    await callback.answer(f"Новый защитный PIN: {new_pin}", show_alert=True)
    await callback.message.edit_text(
        "PIN обновлен. Передайте его только проверенным модераторам.",
        reply_markup=admin_menu_keyboard(),
    )


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(router)

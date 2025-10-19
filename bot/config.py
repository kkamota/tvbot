from dataclasses import dataclass
import json
import logging
import os
from typing import Mapping, Sequence


@dataclass(slots=True)
class Settings:
    bot_token: str
    channel_username: str
    admin_ids: Sequence[int]
    min_withdrawal: int = 15
    start_bonus: int = 3
    referral_bonus: int = 3
    daily_bonus: int = 1
    flyer_api_key: str | None = None
    flyer_language_code: str | None = None
    flyer_check_message: Mapping[str, str] | None = None
    flyer_tasks_message: str | None = None
    flyer_buttons_per_row: int = 2
    flyer_button_labels: Mapping[str, str] | None = None
    flyer_verify_button_text: str = "☑️ Проверить"
    flyer_tasks_limit: int = 5


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "PLACE-YOUR-TOKEN-HERE")
    channel = os.getenv("CHANNEL_USERNAME", "@example_channel")
    raw_admins = os.getenv("ADMIN_IDS", "")
    admin_ids = tuple(
        int(admin_id.strip())
        for admin_id in raw_admins.split(",")
        if admin_id.strip().isdigit()
    )
    flyer_key = os.getenv("FLYER_API_KEY")
    flyer_language = os.getenv("FLYER_LANGUAGE_CODE")

    check_message_raw = os.getenv("FLYER_CHECK_MESSAGE")
    flyer_check_message = None
    if check_message_raw:
        try:
            parsed = json.loads(check_message_raw)
            if isinstance(parsed, dict):
                flyer_check_message = {
                    str(key): str(value) for key, value in parsed.items()
                }
        except json.JSONDecodeError:
            logging.getLogger(__name__).warning(
                "Invalid JSON provided for FLYER_CHECK_MESSAGE"
            )

    tasks_message = os.getenv(
        "FLYER_TASKS_MESSAGE",
        "Чтобы получить доступ к функциям бота, необходимо подписаться на ресурсы.",
    )

    buttons_per_row = os.getenv("FLYER_BUTTONS_PER_ROW")
    try:
        flyer_buttons_per_row = int(buttons_per_row) if buttons_per_row else 2
    except ValueError:
        logging.getLogger(__name__).warning(
            "Invalid FLYER_BUTTONS_PER_ROW value: %s", buttons_per_row
        )
        flyer_buttons_per_row = 2

    button_labels_raw = os.getenv("FLYER_BUTTON_LABELS")
    flyer_button_labels = None
    if button_labels_raw:
        try:
            parsed = json.loads(button_labels_raw)
            if isinstance(parsed, dict):
                flyer_button_labels = {
                    str(key): str(value) for key, value in parsed.items()
                }
        except json.JSONDecodeError:
            logging.getLogger(__name__).warning(
                "Invalid JSON provided for FLYER_BUTTON_LABELS"
            )

    verify_button_text = os.getenv("FLYER_VERIFY_BUTTON_TEXT", "☑️ Проверить")

    tasks_limit_value = os.getenv("FLYER_TASKS_LIMIT")
    try:
        flyer_tasks_limit = int(tasks_limit_value) if tasks_limit_value else 5
    except ValueError:
        logging.getLogger(__name__).warning(
            "Invalid FLYER_TASKS_LIMIT value: %s", tasks_limit_value
        )
        flyer_tasks_limit = 5

    return Settings(
        bot_token=token,
        channel_username=channel,
        admin_ids=admin_ids or (123456789,),
        flyer_api_key=flyer_key,
        flyer_language_code=flyer_language,
        flyer_check_message=flyer_check_message,
        flyer_tasks_message=tasks_message,
        flyer_buttons_per_row=flyer_buttons_per_row,
        flyer_button_labels=flyer_button_labels,
        flyer_verify_button_text=verify_button_text,
        flyer_tasks_limit=flyer_tasks_limit,
    )

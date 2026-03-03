from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards import main_menu_keyboard
from db.engine import get_session
from db.repository import SettingsRepository

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, app) -> None:
    await app.add_subscriber(message.chat.id)

    async with get_session() as session:
        repo = SettingsRepository(session)
        settings = await repo.get_or_create()

    filter_parts = []
    if settings.min_amount is not None:
        filter_parts.append(f"от {settings.min_amount:,.0f}")
    if settings.max_amount is not None:
        filter_parts.append(f"до {settings.max_amount:,.0f}")
    filter_line = (
        f"Фильтр суммы: {' '.join(filter_parts)} ₽"
        if filter_parts
        else "Фильтр суммы: не задан"
    )

    status_line = "Статус: ✅ работает" if app.is_monitoring else "Статус: ⛔ остановлен"

    await message.answer(
        f"<b>Cards2cards бот</b>\n\n"
        f"{status_line}\n"
        f"{filter_line}\n"
        "Уведомления о взятых ордерах: всегда включены",
        reply_markup=main_menu_keyboard(app.is_monitoring),
    )

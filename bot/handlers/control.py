from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.keyboards import main_menu_keyboard
from db.engine import get_session
from db.repository import OrderLogRepository

router = Router()


@router.callback_query(F.data == "bot:start")
async def bot_start(callback: CallbackQuery, app) -> None:
    if app.is_monitoring:
        await callback.answer("Бот уже запущен.", show_alert=True)
        return

    app.set_last_starter(callback.message.chat.id)

    await callback.message.edit_text("Запускаю бота, подождите...")
    await app.start_monitoring()
    await callback.message.edit_text(
        "✅ Бот запущен. Начинаю мониторинг новых ордеров.",
        reply_markup=main_menu_keyboard(True),
    )
    await callback.answer()


@router.callback_query(F.data == "bot:stop")
async def bot_stop(callback: CallbackQuery, app) -> None:
    if not app.is_monitoring:
        await callback.answer("Бот уже остановлен.", show_alert=True)
        return

    await callback.message.edit_text("Останавливаю бота...")
    await app.stop_monitoring()
    await callback.message.edit_text(
        "⛔ Бот остановлен.",
        reply_markup=main_menu_keyboard(False),
    )
    await callback.answer()


@router.callback_query(F.data == "stats:show")
async def stats_show(callback: CallbackQuery) -> None:
    async with get_session() as session:
        log_repo = OrderLogRepository(session)
        taken  = await log_repo.count_taken()
        failed = await log_repo.count_failed()
        last   = await log_repo.last_entries(5)

    lines = [
        "<b>Статистика</b>\n",
        f"Взято ордеров: {taken}",
        f"Ошибок: {failed}",
    ]

    if last:
        lines.append("\nПоследние 5 записей:")
        for entry in last:
            amount_str = f"{entry.amount:,.0f} RUB" if entry.amount else "—"
            dt_str = entry.taken_at.strftime("%d.%m %H:%M")
            icon = "✅" if entry.status == "taken" else "❌"
            lines.append(
                f"{icon} {dt_str}  {amount_str}  <code>{entry.order_slug[:20]}…</code>"
            )

    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data.startswith("retry:"))
async def retry_order(callback: CallbackQuery, app) -> None:
    slug = callback.data.split(":", 1)[1]

    if not app.is_monitoring:
        await callback.answer("Бот не запущен, повтор невозможен.", show_alert=True)
        return

    app.retry_order(slug)
    await callback.message.edit_text(
        f"🔄 Повтор попытки для ордера <code>{slug}</code> запланирован.",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("skip:"))
async def skip_order(callback: CallbackQuery) -> None:
    slug = callback.data.split(":", 1)[1]
    await callback.message.edit_text(
        f"⏭ Ордер <code>{slug}</code> пропущен.",
    )
    await callback.answer()

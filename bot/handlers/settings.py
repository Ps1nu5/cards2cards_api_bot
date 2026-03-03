from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    cancel_keyboard,
    filters_confirm_keyboard,
    main_menu_keyboard,
    settings_menu_keyboard,
)
from db.engine import get_session
from db.repository import SettingsRepository

router = Router()


class FiltersFSM(StatesGroup):
    min_amount = State()
    max_amount = State()
    confirm    = State()


async def _show_settings_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("⚙️ Настройки:", reply_markup=settings_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "settings:menu")
async def settings_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await _show_settings_menu(callback, state)


@router.callback_query(F.data == "settings:back")
async def settings_back(callback: CallbackQuery, state: FSMContext, app) -> None:
    await state.clear()
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_menu_keyboard(app.is_monitoring),
    )
    await callback.answer()


@router.callback_query(F.data == "settings:filters")
async def filters_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()

    async with get_session() as session:
        repo = SettingsRepository(session)
        settings = await repo.get_or_create()

    min_hint = f" (сейчас: {settings.min_amount:,.0f})" if settings.min_amount else ""
    await callback.message.edit_text(
        f"Введите минимальную сумму ордера (₽){min_hint}.\n"
        "Отправьте <b>-</b> чтобы не ограничивать.",
        reply_markup=cancel_keyboard("settings:menu"),
    )
    await state.set_state(FiltersFSM.min_amount)
    await callback.answer()


@router.message(FiltersFSM.min_amount)
async def filters_min_amount(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if text in ("0", "-", "нет", ""):
        await state.update_data(min_amount=None)
    else:
        try:
            value = float(text.replace(",", ".").replace(" ", ""))
            await state.update_data(min_amount=value if value > 0 else None)
        except ValueError:
            await message.answer(
                "Введите число (например, 1000) или <b>-</b> чтобы пропустить:",
                reply_markup=cancel_keyboard("settings:menu"),
            )
            return

    async with get_session() as session:
        repo = SettingsRepository(session)
        settings = await repo.get_or_create()
    max_hint = f" (сейчас: {settings.max_amount:,.0f})" if settings.max_amount else ""
    await message.answer(
        f"Введите максимальную сумму ордера (₽){max_hint}.\n"
        "Отправьте <b>-</b> чтобы не ограничивать.",
        reply_markup=cancel_keyboard("settings:menu"),
    )
    await state.set_state(FiltersFSM.max_amount)


@router.message(FiltersFSM.max_amount)
async def filters_max_amount(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if text in ("0", "-", "нет", ""):
        await state.update_data(max_amount=None)
    else:
        try:
            value = float(text.replace(",", ".").replace(" ", ""))
            await state.update_data(max_amount=value if value > 0 else None)
        except ValueError:
            await message.answer(
                "Введите число (например, 50000) или <b>-</b> чтобы пропустить:",
                reply_markup=cancel_keyboard("settings:menu"),
            )
            return

    data = await state.get_data()
    min_a = data.get("min_amount")
    max_a = data.get("max_amount")
    min_str = f"{min_a:,.0f} ₽" if min_a else "не задана"
    max_str = f"{max_a:,.0f} ₽" if max_a else "не задана"
    await message.answer(
        f"Проверьте фильтры суммы:\n\n"
        f"Минимум: {min_str}\n"
        f"Максимум: {max_str}",
        reply_markup=filters_confirm_keyboard(),
    )
    await state.set_state(FiltersFSM.confirm)


@router.callback_query(F.data == "filters:save", FiltersFSM.confirm)
async def filters_save(callback: CallbackQuery, state: FSMContext, app) -> None:
    data = await state.get_data()
    await state.clear()

    mn = data.get("min_amount")
    mx = data.get("max_amount")

    async with get_session() as session:
        repo = SettingsRepository(session)
        await repo.update(min_amount=mn, max_amount=mx)

    app.min_amount = mn
    app.max_amount = mx
    if app.is_monitoring:
        await app.stop_monitoring()
        await app.start_monitoring(notify=False)

    await callback.message.edit_text(
        "✅ Фильтры суммы сохранены.",
        reply_markup=settings_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "filters:edit", FiltersFSM.confirm)
async def filters_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "Введите минимальную сумму ордера (₽).\n"
        "Отправьте <b>-</b> чтобы не ограничивать.",
        reply_markup=cancel_keyboard("settings:menu"),
    )
    await state.set_state(FiltersFSM.min_amount)
    await callback.answer()


class PollIntervalFSM(StatesGroup):
    value = State()


@router.callback_query(F.data == "settings:poll_interval")
async def poll_interval_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with get_session() as session:
        repo = SettingsRepository(session)
        settings = await repo.get_or_create()
    await callback.message.edit_text(
        f"⏱ Введите интервал опроса в секундах (сейчас: {settings.poll_interval:g}).\n"
        "Минимум: 0.1, максимум: 60.",
        reply_markup=cancel_keyboard("settings:menu"),
    )
    await state.set_state(PollIntervalFSM.value)
    await callback.answer()


@router.message(PollIntervalFSM.value)
async def poll_interval_set(message: Message, state: FSMContext, app) -> None:
    raw = message.text.strip().replace(",", ".")
    try:
        value = float(raw)
        if not (0.1 <= value <= 60):
            raise ValueError
    except ValueError:
        await message.answer(
            "Введите число от 0.1 до 60 (например, 1 или 0.5):",
            reply_markup=cancel_keyboard("settings:menu"),
        )
        return

    await state.clear()

    async with get_session() as session:
        repo = SettingsRepository(session)
        await repo.update(poll_interval=value)

    app.poll_interval = value
    if app.is_monitoring:
        await app.stop_monitoring()
        await app.start_monitoring(notify=False)

    await message.answer(
        f"✅ Интервал опроса сохранён: {value:g} сек.",
        reply_markup=settings_menu_keyboard(),
    )

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database import get_db, get_all_bookings, confirm_booking, cancel_booking, get_or_create_master, get_masters, get_services
from keyboards import get_admin_menu, get_admin_bookings_keyboard, get_admin_booking_actions, get_back_main
from states import AdminAddMasterState, AdminWorkingHoursState
from config import ADMIN_IDS, ADMIN_USERNAMES
import config

router = Router()


def is_admin(user_id: int, username: str = None) -> bool:
    if user_id in ADMIN_IDS:
        return True
    if username and username in ADMIN_USERNAMES:
        return True
    return False


@router.message(F.text == "/admin")
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id, message.from_user.username):
        await message.answer("⛔ Доступ запрещён")
        return
    
    await message.answer("🔧 Админ-панель:", reply_markup=get_admin_menu())


@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    await callback.message.edit_text("🔧 Админ-панель:", reply_markup=get_admin_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_bookings")
async def admin_bookings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    db = next(get_db())
    bookings = get_all_bookings(db)
    db.close()
    
    if not bookings:
        await callback.message.edit_text(
            "📭 Записей пока нет.",
            reply_markup=get_back_main()
        )
    else:
        await callback.message.edit_text(
            "📋 Все записи:",
            reply_markup=get_admin_bookings_keyboard(bookings)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_booking_"))
async def admin_booking_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    booking_id = int(callback.data.split("_")[-1])
    
    db = next(get_db())
    bookings = get_all_bookings(db)
    booking = next((b for b in bookings if b.id == booking_id), None)
    db.close()
    
    if not booking:
        await callback.answer("Запись не найдена")
        return
    
    status = "⏳ Ожидает" if booking.status == "pending" else "✅ Подтверждена" if booking.status == "confirmed" else "❌ Отменена"
    
    text = (
        f"📋 Запись #{booking.id}\n\n"
        f"👤 Клиент: @{booking.username or booking.full_name or 'Unknown'}\n"
        f"✨ Услуга: {booking.service.name}\n"
        f"💰 Цена: {booking.service.price} ₽\n"
        f"👤 Мастер: {booking.master.name}\n"
        f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
        f"🕐 Время: {booking.time.strftime('%H:%M')}\n"
        f"📌 Статус: {status}"
    )
    
    await callback.message.edit_text(text, reply_markup=get_admin_booking_actions(booking_id))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    booking_id = int(callback.data.split("_")[-1])
    
    db = next(get_db())
    success = confirm_booking(db, booking_id)
    db.close()
    
    if success:
        await callback.message.edit_text("✅ Запись подтверждена!", reply_markup=get_admin_menu())
    else:
        await callback.answer("Не удалось подтвердить запись")
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    booking_id = int(callback.data.split("_")[-1])
    
    db = next(get_db())
    success = cancel_booking(db, booking_id)
    db.close()
    
    if success:
        await callback.message.edit_text("❌ Запись отменена!", reply_markup=get_admin_menu())
    else:
        await callback.answer("Не удалось отменить запись")
    
    await callback.answer()


@router.callback_query(F.data == "admin_add_master")
async def admin_add_master_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    await callback.message.edit_text("👥 Добавление мастера\n\nВведите имя мастера:")
    await state.set_state(AdminAddMasterState.name)
    await callback.answer()


@router.message(AdminAddMasterState.name)
async def admin_add_master_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите username мастера (без @):")
    await state.set_state(AdminAddMasterState.username)


@router.message(AdminAddMasterState.username)
async def admin_add_master_username(message: Message, state: FSMContext):
    username = message.text.strip().lstrip("@")
    await state.update_data(username=username)
    await message.answer("Введите описание мастера:")
    await state.set_state(AdminAddMasterState.bio)


@router.message(AdminAddMasterState.bio)
async def admin_add_master_bio(message: Message, state: FSMContext):
    data = await state.get_data()
    
    db = next(get_db())
    master = get_or_create_master(db, data["name"], data["username"], message.text)
    db.close()
    
    await message.answer(f"✅ Мастер '{master.name}' добавлен!", reply_markup=get_admin_menu())
    await state.clear()


@router.callback_query(F.data == "admin_hours")
async def admin_hours(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    await callback.message.edit_text(
        f"⏰ Текущие рабочие часы:\n"
        f"Начало: {config.WORKING_HOURS_START}:00\n"
        f"Конец: {config.WORKING_HOURS_END}:00\n\n"
        f"Введите час начала работы (0-23):"
    )
    await state.set_state(AdminWorkingHoursState.start_hour)
    await callback.answer()


@router.message(AdminWorkingHoursState.start_hour)
async def admin_hours_start(message: Message, state: FSMContext):
    try:
        hour = int(message.text)
        if 0 <= hour <= 23:
            await state.update_data(start_hour=hour)
            await message.answer("Введите час окончания работы (0-23):")
            await state.set_state(AdminWorkingHoursState.end_hour)
        else:
            await message.answer("Введите число от 0 до 23")
    except ValueError:
        await message.answer("Введите число")


@router.message(AdminWorkingHoursState.end_hour)
async def admin_hours_end(message: Message, state: FSMContext):
    try:
        hour = int(message.text)
        if 0 <= hour <= 23:
            data = await state.get_data()
            
            await message.answer(
                f"✅ Рабочие часы обновлены:\n"
                f"Начало: {data['start_hour']}:00\n"
                f"Конец: {hour}:00\n\n"
                f"Перезапустите бота для применения изменений.",
                reply_markup=get_admin_menu()
            )
            await state.clear()
        else:
            await message.answer("Введите число от 0 до 23")
    except ValueError:
        await message.answer("Введите число")


@router.callback_query(F.data == "admin_services")
async def admin_services(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    db = next(get_db())
    services = get_services(db)
    db.close()
    
    text = "✨ Услуги:\n\n"
    for s in services:
        text += f"• {s.name} — {s.price} ₽ ({s.duration_minutes} мин)\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_masters")
async def admin_masters(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    db = next(get_db())
    masters = get_masters(db)
    db.close()
    
    text = "👥 Мастера:\n\n"
    for m in masters:
        text += f"• {m.name} (@{m.username or 'N/A'})\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_menu())
    await callback.answer()

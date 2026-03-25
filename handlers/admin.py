from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import date, datetime
import logging

from database import get_db, get_all_bookings, confirm_booking, cancel_booking, get_or_create_master, get_masters, delete_master, get_master_by_id, get_services, delete_service, get_service_by_id, create_service, get_booking_by_id, update_booking_service, delete_booking, reschedule_booking
from keyboards import get_admin_menu, get_admin_bookings_keyboard, get_admin_booking_actions, get_back_main, get_masters_management_keyboard, get_services_management_keyboard
from states import AdminAddMasterState, AdminWorkingHoursState, AdminAddServiceState, AdminRescheduleState
from config import ADMIN_IDS
from config import ADMIN_IDS, ADMIN_USERNAMES
import config

router = Router()
logger = logging.getLogger(__name__)


def is_admin(user_id: int, username: str = None) -> bool:
    if user_id in ADMIN_IDS:
        return True
    if username and username in ADMIN_USERNAMES:
        return True
    return False


def check_admin(callback_or_message):
    user = callback_or_message.from_user
    return is_admin(user.id, user.username)


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
    
    logger.info("Admin requesting all bookings")
    
    db = next(get_db())
    try:
        bookings = get_all_bookings(db)
        logger.info(f"Found {len(bookings)} total bookings")
        
        if not bookings:
            await callback.message.edit_text(
                "📭 Записей пока нет.",
                reply_markup=get_back_main()
            )
        else:
            await callback.message.edit_text(
                f"📋 Все записи ({len(bookings)}):",
                reply_markup=get_admin_bookings_keyboard(bookings)
            )
    except Exception as e:
        logger.error(f"Error getting all bookings: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка: {e}",
            reply_markup=get_back_main()
        )
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_booking_"))
async def admin_booking_detail(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    await state.clear()
    
    try:
        data = callback.data
        logger.info(f"Admin callback: {data}")
        
        booking_id = int(callback.data.split("_")[-1])
        
        db = next(get_db())
        try:
            booking = get_booking_by_id(db, booking_id)
            
            if not booking:
                await callback.answer("Запись не найдена", show_alert=True)
                return
            
            from keyboards.main import get_booking_card_text
            text = get_booking_card_text(booking, show_full_info=True)
            
            await callback.message.edit_text(text, reply_markup=get_admin_booking_detail_keyboard(booking_id))
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in admin_booking_detail: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)
    
    await callback.answer()


def get_admin_booking_detail_keyboard(booking_id: int):
    """Кнопки для карточки записи в админке"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Написать клиенту", callback_data=f"admin_write_{booking_id}")],
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{booking_id}")],
        [InlineKeyboardButton(text="🔄 Изменить время", callback_data=f"admin_edit_time_{booking_id}")],
        [InlineKeyboardButton(text="💅 Изменить услугу", callback_data=f"admin_edit_service_{booking_id}")],
        [InlineKeyboardButton(text="❌ Удалить запись", callback_data=f"admin_delete_{booking_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_bookings")]
    ])


@router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    booking_id = int(callback.data.split("_")[-1])
    logger.info(f"Admin confirming booking {booking_id}")
    
    db = next(get_db())
    success, user_data = confirm_booking(db, booking_id)
    
    if success and user_data:
        # Отправляем уведомление пользователю
        try:
            await callback.bot.send_message(
                user_data["user_id"],
                "✅ Ваша запись подтверждена!\n\n"
                "Мы ждём вас в назначенное время.\n"
                "До встречи!"
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
    
    db.close()
    
    if success:
        await callback.message.edit_text("✅ Запись подтверждена! Клиент уведомлён.", reply_markup=get_admin_menu())
    else:
        await callback.message.edit_text("❌ Не удалось подтвердить запись", reply_markup=get_admin_menu())
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    booking_id = int(callback.data.split("_")[-1])
    logger.info(f"Admin cancelling booking {booking_id}")
    
    db = next(get_db())
    success, user_data = cancel_booking(db, booking_id)
    
    if success and user_data:
        # Отправляем уведомление пользователю
        try:
            await callback.bot.send_message(
                user_data["user_id"],
                "К сожалению, ваша запись отменена.\n\n"
                "Это время занято. Свяжитесь с нами для подбора другого времени."
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
    
    db.close()
    
    if success:
        await callback.message.edit_text("❌ Запись отменена! Клиент уведомлён.", reply_markup=get_admin_menu())
    else:
        await callback.message.edit_text("❌ Не удалось отменить запись", reply_markup=get_admin_menu())
    
    await callback.answer()


@router.callback_query(F.data == "admin_manage_masters")
async def admin_manage_masters(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    db = next(get_db())
    masters = get_masters(db)
    db.close()
    
    if not masters:
        await callback.message.edit_text(
            "👥 Нет мастеров. Добавьте первого мастера:",
            reply_markup=get_masters_management_keyboard([])
        )
    else:
        await callback.message.edit_text(
            "👥 Управление мастерами:",
            reply_markup=get_masters_management_keyboard(masters)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_master_"))
async def admin_delete_master(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    master_id = int(callback.data.split("_")[-1])
    logger.info(f"Admin deleting master {master_id}")
    
    db = next(get_db())
    master = get_master_by_id(db, master_id)
    if master:
        success = delete_master(db, master_id)
        db.close()
        if success:
            await callback.message.edit_text(f"✅ Мастер '{master.name}' удалён!", reply_markup=get_admin_menu())
        else:
            await callback.message.edit_text("❌ Не удалось удалить мастера", reply_markup=get_admin_menu())
    else:
        db.close()
        await callback.message.edit_text("❌ Мастер не найден", reply_markup=get_admin_menu())
    
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
    logger.info(f"Adding master: {data['name']}, @{data['username']}")
    
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


@router.callback_query(F.data == "admin_dates")
async def admin_dates(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    await callback.message.edit_text(
        "📅 Управление датами\n\n"
        "Даты автоматически генерируются на 14 дней вперёд.\n"
        "Свободные слоты отображаются при записи клиента.",
        reply_markup=get_admin_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_manage_services")
async def admin_manage_services(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    db = next(get_db())
    services = get_services(db)
    db.close()
    
    if not services:
        await callback.message.edit_text(
            "✨ Нет услуг. Добавьте первую услугу:",
            reply_markup=get_services_management_keyboard([])
        )
    else:
        await callback.message.edit_text(
            "✨ Управление услугами:",
            reply_markup=get_services_management_keyboard(services)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_service_"))
async def admin_delete_service(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    service_id = int(callback.data.split("_")[-1])
    logger.info(f"Admin deleting service {service_id}")
    
    db = next(get_db())
    service = get_service_by_id(db, service_id)
    if service:
        success = delete_service(db, service_id)
        db.close()
        if success:
            await callback.message.edit_text(f"✅ Услуга '{service.name}' удалена!", reply_markup=get_admin_menu())
        else:
            await callback.message.edit_text("❌ Не удалось удалить услугу", reply_markup=get_admin_menu())
    else:
        db.close()
        await callback.message.edit_text("❌ Услуга не найдена", reply_markup=get_admin_menu())
    
    await callback.answer()


@router.callback_query(F.data == "admin_add_service")
async def admin_add_service_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    await callback.message.edit_text("✨ Добавление услуги\n\nВведите название услуги:")
    await state.set_state(AdminAddServiceState.name)
    await callback.answer()


@router.message(AdminAddServiceState.name)
async def admin_add_service_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите цену услуги (число):")
    await state.set_state(AdminAddServiceState.price)


@router.message(AdminAddServiceState.price)
async def admin_add_service_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        await state.update_data(price=price)
        await message.answer("Введите описание услуги (или /skip чтобы пропустить):")
        await state.set_state(AdminAddServiceState.description)
    except ValueError:
        await message.answer("Введите число!")


@router.message(AdminAddServiceState.description)
async def admin_add_service_desc(message: Message, state: FSMContext):
    data = await state.get_data()
    description = message.text if message.text != "/skip" else None
    
    logger.info(f"Adding service: {data['name']}, price: {data['price']}")
    
    db = next(get_db())
    service = create_service(db, data["name"], data["price"], description)
    db.close()
    
    await message.answer(f"✅ Услуга '{service.name}' за {service.price} ₽ добавлена!", reply_markup=get_admin_menu())
    await state.clear()


# Обработчики для карточки записи админа
@router.callback_query(F.data.startswith("admin_write_"))
async def admin_write_client(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    booking_id = int(callback.data.split("_")[-1])
    
    db = next(get_db())
    booking = get_booking_by_id(db, booking_id)
    db.close()
    
    if not booking:
        await callback.answer("Запись не найдена")
        return
    
    # Открываем чат с пользователем
    await callback.message.edit_text(
        f"📱 Напишите клиенту:\n"
        f"tg://user?id={booking.user_id}\n\n"
        f"Или нажмите на ссылку выше.",
        reply_markup=get_admin_booking_detail_keyboard(booking_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_time_"))
async def admin_edit_time_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    booking_id = int(callback.data.split("_")[-1])
    
    db = next(get_db())
    booking = get_booking_by_id(db, booking_id)
    if not booking:
        await callback.answer("Запись не найдена")
        db.close()
        return
    
    master_id = booking.master_id
    current_date = booking.date.strftime('%d.%m.%Y')
    current_time = booking.time.strftime('%H:%M')
    db.close()
    
    # Сохраняем в state
    await state.update_data(booking_id=booking_id, master_id=master_id)
    await state.set_state(AdminRescheduleState.new_date)
    
    from keyboards.calendar import get_calendar_keyboard
    await callback.message.edit_text(
        f"📅 Текущее время: {current_date} {current_time}\n\n"
        f"Выберите новую дату для записи #{booking_id}:",
        reply_markup=get_calendar_keyboard(master_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_service_"))
async def admin_edit_service(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    booking_id = int(callback.data.split("_")[-1])
    
    db = next(get_db())
    booking = get_booking_by_id(db, booking_id)
    if not booking:
        await callback.answer("Запись не найдена")
        db.close()
        return
    
    services = get_services(db)
    db.close()
    
    # Создаем клавиатуру с услугами
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.button(
            text=f"{service.name} — {service.price} ₽",
            callback_data=f"admin_set_service_{booking_id}_{service.id}"
        )
    builder.button(text="◀️ Назад", callback_data=f"admin_booking_{booking_id}")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"💅 Выберите новую услугу для записи #{booking_id}:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_set_service_"))
async def admin_set_service(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    parts = callback.data.split("_")
    booking_id = int(parts[-2])
    new_service_id = int(parts[-1])
    
    db = next(get_db())
    success, error, user_data = update_booking_service(db, booking_id, new_service_id)
    
    if success:
        # Уведомляем клиента
        try:
            await callback.bot.send_message(
                user_data["user_id"],
                "🔔 Администратор изменил услугу в вашей записи.\n\n"
                "Проверьте актуальную информацию в разделе 'Мои записи'."
            )
        except:
            pass
        
        await callback.message.edit_text(
            f"✅ Услуга изменена!",
            reply_markup=get_admin_menu()
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка: {error}",
            reply_markup=get_admin_menu()
        )
    
    db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_"))
async def admin_delete_booking(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    booking_id = int(callback.data.split("_")[-1])
    
    db = next(get_db())
    success, user_data = delete_booking(db, booking_id)
    
    if success and user_data:
        # Уведомляем клиента
        try:
            await callback.bot.send_message(
                user_data["user_id"],
                "❌ Ваша запись была удалена администратором.\n\n"
                "Свяжитесь с нами для оформления новой записи."
            )
        except:
            pass
    
    db.close()
    
    if success:
        await callback.message.edit_text(
            f"✅ Запись #{booking_id} удалена!",
            reply_markup=get_admin_menu()
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось удалить запись",
            reply_markup=get_admin_menu()
        )
    
    await callback.answer()


# Обработчик выбора даты при переносе админом
@router.callback_query(F.data.startswith("calendar_"), AdminRescheduleState.new_date)
async def admin_reschedule_date(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    parts = callback.data.split("_")
    if len(parts) < 3:
        return
    
    date_str = parts[2]
    selected_date = date.fromisoformat(date_str)
    
    await state.update_data(new_date=date_str, new_selected_date=selected_date)
    await state.set_state(AdminRescheduleState.new_time)
    
    data = await state.get_data()
    master_id = data.get("master_id")
    booking_id = data.get("booking_id")
    
    if not master_id or not booking_id:
        await callback.answer("Ошибка: данные не найдены")
        return
    
    # Получаем свободные слоты
    db = next(get_db())
    from database import get_available_slots
    slots = get_available_slots(db, master_id, selected_date)
    db.close()
    
    if not slots:
        await callback.message.edit_text(
            f"❌ Нет свободных слотов на {date_str}",
            reply_markup=get_admin_menu()
        )
    else:
        from keyboards.main import get_time_slots_keyboard
        await callback.message.edit_text(
            f"🕐 Выберите время:",
            reply_markup=get_time_slots_keyboard(slots, date_str, master_id)
        )
    
    await callback.answer()


# Обработчик выбора времени при переносе
@router.callback_query(F.data.startswith("time_"), AdminRescheduleState.new_time)
async def admin_reschedule_time(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("⛔ Доступ запрещён")
        return
    
    parts = callback.data.split("_")
    date_str = parts[1]
    time_str = parts[2]
    master_id = int(parts[3])
    
    selected_time = datetime.strptime(time_str, "%H:%M").time()
    selected_date = date.fromisoformat(date_str)
    
    data = await state.get_data()
    booking_id = data.get("booking_id")
    
    if not booking_id:
        await callback.answer("Ошибка: ID записи не найден")
        return
    
    logger.info(f"Admin rescheduling booking {booking_id} to {date_str} {time_str}")
    
    db = next(get_db())
    success, error, user_data = reschedule_booking(db, booking_id, selected_date, selected_time)
    
    if success and user_data:
        # Уведомляем клиента
        try:
            await callback.bot.send_message(
                user_data["user_id"],
                f"🔔 Администратор перенёс вашу запись!\n\n"
                f"📅 Новая дата: {date_str}\n"
                f"🕐 Новое время: {time_str}\n\n"
                f"Ждём вас!"
            )
        except:
            pass
    
    db.close()
    
    if success:
        await callback.message.edit_text(
            f"✅ Время изменено! Клиент уведомлён.",
            reply_markup=get_admin_menu()
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка: {error}",
            reply_markup=get_admin_menu()
        )
    
    await state.clear()
    await callback.answer()

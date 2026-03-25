from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import date, time, datetime
import logging

from database import get_db, get_services, get_masters, get_available_slots, create_booking, get_user_bookings, cancel_booking, get_booking_by_id, reschedule_booking
from keyboards import get_main_menu, get_services_keyboard, get_masters_keyboard, get_time_slots_keyboard, get_calendar_keyboard, get_my_bookings_keyboard, get_booking_detail_keyboard, get_back_main, get_back_to_bookings, get_contacts_keyboard, get_help_keyboard
from states import BookingState, RescheduleState, AdminRescheduleState
from config import ADMIN_IDS
import config

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "👋 Добро пожаловать в салон красоты!\n\nВыберите действие:",
        reply_markup=get_main_menu()
    )


@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👋 Выберите действие:",
        reply_markup=get_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "book_appointment")
async def book_appointment(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    db = next(get_db())
    services = get_services(db)
    db.close()
    
    if not services:
        await callback.message.edit_text(
            "😔 Услуги временно недоступны. Попробуйте позже.",
            reply_markup=get_main_menu()
        )
    else:
        await callback.message.edit_text(
            "✨ Выберите услугу:",
            reply_markup=get_services_keyboard(services)
        )
    await callback.answer()


@router.callback_query(F.data == "back_services")
async def back_services(callback: CallbackQuery):
    db = next(get_db())
    services = get_services(db)
    db.close()
    
    await callback.message.edit_text(
        "✨ Выберите услугу:",
        reply_markup=get_services_keyboard(services)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("service_"))
async def select_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[1])
    db = next(get_db())
    services = get_services(db)
    service = next((s for s in services if s.id == service_id), None)
    db.close()
    
    if not service:
        await callback.answer("Услуга не найдена")
        return
    
    await state.update_data(service_id=service_id, service_name=service.name, service_price=service.price)
    logger.info(f"User selected service: {service.name}")
    
    db = next(get_db())
    masters = get_masters(db)
    db.close()
    
    if not masters:
        await callback.message.edit_text(
            "😔 Мастера временно недоступны.",
            reply_markup=get_main_menu()
        )
    else:
        await callback.message.edit_text(
            "👤 Выберите мастера:",
            reply_markup=get_masters_keyboard(masters)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("master_"))
async def select_master(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_")[1])
    db = next(get_db())
    masters = get_masters(db)
    master = next((m for m in masters if m.id == master_id), None)
    db.close()
    
    if not master:
        await callback.answer("Мастер не найден")
        return
    
    await state.update_data(master_id=master_id, master_name=master.name)
    await state.set_state(BookingState.date)
    logger.info(f"User selected master: {master.name}")
    
    await callback.message.edit_text(
        "📅 Выберите дату:",
        reply_markup=get_calendar_keyboard(master_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("calendar_"), BookingState.date)
async def select_date(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    master_id = int(parts[1])
    date_str = parts[2]
    selected_date = date.fromisoformat(date_str)
    
    await state.update_data(date=date_str, selected_date=selected_date)
    await state.set_state(BookingState.time)
    
    db = next(get_db())
    slots = get_available_slots(db, master_id, selected_date)
    db.close()
    
    if not slots:
        await callback.message.edit_text(
            f"❌ Нет свободных слотов на {date_str}.\nВыберите другую дату:",
            reply_markup=get_calendar_keyboard(master_id)
        )
    else:
        await callback.message.edit_text(
            f"📅 {date_str}\n🕐 Выберите время:",
            reply_markup=get_time_slots_keyboard(slots, date_str, master_id)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("time_"), BookingState.time)
async def select_time(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    date_str = parts[1]
    time_str = parts[2]
    master_id = int(parts[3])
    
    selected_time = datetime.strptime(time_str, "%H:%M").time()
    selected_date = date.fromisoformat(date_str)
    
    await state.update_data(
        time=time_str, 
        selected_time=selected_time, 
        selected_date=selected_date,
        master_id=master_id
    )
    
    logger.info(f"User selected time: {date_str} {time_str}, master_id: {master_id}")
    
    # Переходим к вводу имени
    await callback.message.edit_text(
        "📝 Введите ваше имя:",
        reply_markup=get_back_main()
    )
    await state.set_state(BookingState.name)
    await callback.answer()


@router.message(BookingState.name)
async def input_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Введите имя (минимум 2 символа):")
        return
    
    await state.update_data(name=name)
    logger.info(f"User entered name: {name}")
    
    await message.answer("📱 Введите ваш номер телефона:")
    await state.set_state(BookingState.phone)


@router.message(BookingState.phone)
async def input_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if len(phone) < 5:
        await message.answer("Введите корректный номер телефона:")
        return
    
    await state.update_data(phone=phone)
    logger.info(f"User entered phone: {phone}")
    
    await message.answer(
        "💬 Введите комментарий (или /skip чтобы пропустить):\n"
        "Например: хочу французский маникюр"
    )
    await state.set_state(BookingState.comment)


@router.message(BookingState.comment)
async def input_comment(message: Message, state: FSMContext):
    if message.text and message.text.strip() != "/skip":
        comment = message.text.strip()
    else:
        comment = None
    
    await state.update_data(comment=comment)
    logger.info(f"User entered comment: {comment}")
    
    # Показываем подтверждение
    data = await state.get_data()
    
    db = next(get_db())
    services = get_services(db)
    service = next((s for s in services if s.id == data["service_id"]), None)
    masters = get_masters(db)
    master = next((m for m in masters if m.id == data["master_id"]), None)
    db.close()
    
    confirmation_text = (
        f"📋 Подтверждение записи:\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"✨ Услуга: {service.name}\n"
        f"💰 Цена: {service.price} ₽\n"
        f"👤 Мастер: {master.name}\n"
        f"📅 Дата: {data['date']}\n"
        f"🕐 Время: {data['time']}\n"
    )
    
    if data.get('comment'):
        confirmation_text += f"💬 Комментарий: {data['comment']}\n"
    
    confirmation_text += "\n✅ Подтвердить запись?"
    
    from keyboards.main import get_booking_confirmation
    keyboard = get_booking_confirmation(data['date'], data['time'], data['master_id'])
    
    await message.answer(confirmation_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("confirm_"))
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    date_str = parts[1]
    time_str = parts[2]
    master_id = int(parts[3])
    
    selected_time = datetime.strptime(time_str, "%H:%M").time()
    selected_date = date.fromisoformat(date_str)
    
    data = await state.get_data()
    user = callback.from_user
    
    logger.info(f"User {user.id} confirming booking: {date_str} {time_str}")
    
    db = next(get_db())
    try:
        booking, error = create_booking(
            db=db,
            user_id=user.id,
            username=user.username,
            name=data.get("name", user.first_name or "Без имени"),
            phone=data.get("phone", "Не указан"),
            service_id=data["service_id"],
            master_id=master_id,
            date_val=selected_date,
            time_val=selected_time,
            comment=data.get("comment")
        )
        
        if error:
            await callback.message.edit_text(f"❌ {error}", reply_markup=get_main_menu())
            await state.clear()
            await callback.answer()
            return
        
        # Сообщение пользователю
        await callback.message.edit_text(
            f"✅ Заявка отправлена!\n\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}\n"
            f"💅 Услуга: {data['service_name']}\n\n"
            f"Мастер свяжется с вами в ближайшее время.",
            reply_markup=get_main_menu()
        )
        
        # Уведомление админу с красивым сообщением и кнопками
        from keyboards.main import get_admin_booking_actions
        admin_text = (
            f"🔥 Новая заявка\n\n"
            f"Имя: {data.get('name', 'Без имени')}\n"
            f"Телефон: {data.get('phone', 'Не указан')}\n"
            f"Username: @{user.username or 'Нет'}\n"
            f"Услуга: {data['service_name']}\n"
            f"Мастер: {data['master_name']}\n"
            f"Дата: {date_str}\n"
            f"Время: {time_str}\n"
        )
        
        if data.get('comment'):
            admin_text += f"Комментарий: {data['comment']}\n"
        
        admin_text += f"\nID заявки: {booking.id}"
        
        for admin_id in config.ADMIN_IDS:
            try:
                await callback.bot.send_message(
                    admin_id,
                    admin_text,
                    reply_markup=get_admin_booking_actions(booking.id)
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        await callback.message.edit_text(f"❌ Ошибка: {e}", reply_markup=get_main_menu())
    finally:
        db.close()
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_booking")
async def cancel_booking_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Запись отменена.",
        reply_markup=get_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "my_bookings")
async def my_bookings(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    
    logger.info(f"User {user_id} requesting their bookings")
    
    db = next(get_db())
    try:
        bookings = get_user_bookings(db, user_id)
        logger.info(f"Found {len(bookings)} bookings for user {user_id}")
        
        if not bookings:
            await callback.message.edit_text(
                "📭 У вас пока нет записей.",
                reply_markup=get_back_main()
            )
        else:
            text = "📋 Ваши записи:\n\n"
            for b in bookings:
                status = "⏳ Ожидает" if b.status == "pending" else "✅ Подтверждена"
                text += f"{status}\n"
                text += f"✨ {b.service.name}\n"
                text += f"👤 {b.master.name}\n"
                text += f"📅 {b.date.strftime('%d.%m.%Y')} {b.time.strftime('%H:%M')}\n\n"
            
            await callback.message.edit_text(text, reply_markup=get_my_bookings_keyboard(bookings))
    except Exception as e:
        logger.error(f"Error getting user bookings: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка: {e}",
            reply_markup=get_back_main()
        )
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data.startswith("booking_detail_"))
async def booking_detail(callback: CallbackQuery, state: FSMContext):
    # Всегда очищаем состояние при нажатии на кнопку
    await state.clear()
    
    try:
        data = callback.data
        logger.info(f"Callback received: {data}")
        
        # Разбираем callback_data: booking_detail_123
        parts = data.split("_")
        booking_id = int(parts[2])
        
        logger.info(f"Opening booking {booking_id} for user {callback.from_user.id}")
        
        db = next(get_db())
        try:
            bookings = get_user_bookings(db, callback.from_user.id)
            booking = next((b for b in bookings if b.id == booking_id), None)
            
            if not booking:
                await callback.answer("Запись не найдена", show_alert=True)
                return
            
            from keyboards.main import get_booking_card_text
            text = get_booking_card_text(booking, show_full_info=True)
            
            await callback.message.edit_text(text, reply_markup=get_booking_detail_keyboard(booking_id, is_admin=False, admin_id=config.ADMIN_IDS[0] if config.ADMIN_IDS else None))
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in booking_detail: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_"))
async def cancel_user_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[1])
    logger.info(f"User cancelling booking {booking_id}")
    
    db = next(get_db())
    success, user_data = cancel_booking(db, booking_id)
    db.close()
    
    if success:
        # Уведомляем админа
        for admin_id in config.ADMIN_IDS:
            try:
                await callback.bot.send_message(
                    admin_id,
                    f"❌ Клиент отменил запись #{booking_id}"
                )
            except:
                pass
        
        await callback.message.edit_text(
            "❌ Запись отменена.\n\nМы будем рады видеть вас в другое время!",
            reply_markup=get_back_to_bookings()
        )
    else:
        await callback.answer("Не удалось отменить запись")
    
    await callback.answer()


@router.callback_query(F.data.startswith("reschedule_"))
async def reschedule_booking_start(callback: CallbackQuery, state: FSMContext):
    booking_id = int(callback.data.split("_")[1])
    
    # Получаем запись из базы
    db = next(get_db())
    booking = get_booking_by_id(db, booking_id)
    if not booking:
        await callback.answer("Запись не найдена")
        db.close()
        return
    
    # Сохраняем booking_id и master_id в state
    await state.update_data(booking_id=booking_id, master_id=booking.master_id)
    await state.set_state(RescheduleState.new_date)
    
    master_id = booking.master_id
    current_date = booking.date.strftime('%d.%m.%Y')
    current_time = booking.time.strftime('%H:%M')
    db.close()
    
    from keyboards.calendar import get_calendar_keyboard
    await callback.message.edit_text(
        f"📅 Текущее время: {current_date} {current_time}\n\n"
        f"Выберите новую дату:",
        reply_markup=get_calendar_keyboard(master_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("client_contact_"))
async def client_contact(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[2])
    
    db = next(get_db())
    booking = get_booking_by_id(db, booking_id)
    db.close()
    
    if not booking:
        await callback.answer("Запись не найдена")
        return
    
    # Ссылка для связи с мастером
    master_username = booking.master.username if booking.master else "username"
    
    await callback.message.edit_text(
        f"📱 Для связи с мастером:\n\n"
        f"Напишите @{master_username}\n"
        f"или позвоните по телефону салона.",
        reply_markup=get_back_to_bookings()
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
    text = (
        "❓ Помощь\n\n"
        "📅 Для записи нажмите 'Записаться'\n"
        "📋 Чтобы посмотреть свои записи - 'Мои записи'\n"
        "❌ Для отмены записи выберите её в 'Мои записи'\n"
        "🔄 Для переноса выберите 'Перенести'\n\n"
        "Контакты:\n"
        f"📱 @{config.ADMIN_USERNAME}\n"
        f"📞 {config.ADMIN_PHONE}"
    )
    
    await callback.message.edit_text(text, reply_markup=get_help_keyboard())
    await callback.answer()


@router.callback_query(F.data == "contacts")
async def contacts_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "📞 Контакты:\n\n"
        "📱 @username\n"
        "📞 +7 (999) 000-00-00\n"
        "📍 Адрес: ул. Примерная, д. 1",
        reply_markup=get_contacts_keyboard()
    )
    await callback.answer()


# FSM для изменения времени записи - выбор даты
@router.callback_query(F.data.startswith("calendar_"), RescheduleState.new_date)
async def reschedule_select_date(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    date_str = parts[2]
    selected_date = date.fromisoformat(date_str)
    
    await state.update_data(new_date=date_str, new_selected_date=selected_date)
    await state.set_state(RescheduleState.new_time)
    
    data = await state.get_data()
    master_id = data.get("master_id")
    
    if not master_id:
        await callback.answer("Ошибка: мастер не найден")
        return
    
    # Показываем свободные слоты
    db = next(get_db())
    slots = get_available_slots(db, master_id, selected_date)
    db.close()
    
    if not slots:
        await callback.message.edit_text(
            f"❌ Нет свободных слотов на {date_str}",
            reply_markup=get_back_to_bookings()
        )
    else:
        await callback.message.edit_text(
            f"🕐 Выберите время:",
            reply_markup=get_time_slots_keyboard(slots, date_str, master_id)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("time_"), RescheduleState.new_time)
async def reschedule_select_time(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    date_str = parts[1]
    time_str = parts[2]
    master_id = int(parts[3])
    
    selected_time = datetime.strptime(time_str, "%H:%M").time()
    selected_date = date.fromisoformat(date_str)
    
    data = await state.get_data()
    booking_id = data.get("booking_id")
    
    logger.info(f"Rescheduling booking {booking_id} to {date_str} {time_str}")
    
    db = next(get_db())
    success, error, user_data = reschedule_booking(db, booking_id, selected_date, selected_time)
    
    if success:
        # Уведомляем админа
        for admin_id in config.ADMIN_IDS:
            try:
                await callback.bot.send_message(
                    admin_id,
                    f"🔄 Клиент перенёс запись #{booking_id}\n"
                    f"Новое время: {date_str} {time_str}"
                )
            except:
                pass
        
        await callback.message.edit_text(
            f"✅ Время изменено!\n\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}\n\n"
            f"Мы свяжемся с вами для подтверждения.",
            reply_markup=get_back_to_bookings()
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка: {error}",
            reply_markup=get_back_to_bookings()
        )
    
    db.close()
    await state.clear()
    await callback.answer()

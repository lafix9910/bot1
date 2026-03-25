from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import date, time, datetime

from database import get_db, get_services, get_masters, get_available_slots, create_booking, get_user_bookings, cancel_booking, reschedule_booking
from keyboards import get_main_menu, get_services_keyboard, get_masters_keyboard, get_time_slots_keyboard, get_calendar_keyboard, get_my_bookings_keyboard, get_booking_detail_keyboard, get_back_main, get_back_to_bookings, get_contacts_keyboard, get_help_keyboard, get_booking_confirmation
from states import BookingState, RescheduleState
from config import ADMIN_IDS
import config

router = Router()


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
    
    await callback.message.edit_text(
        "📅 Выберите дату:",
        reply_markup=get_calendar_keyboard(master_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("calendar_"))
async def select_date(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    master_id = int(parts[1])
    date_str = parts[2]
    selected_date = date.fromisoformat(date_str)
    
    await state.update_data(date=date_str, selected_date=selected_date)
    
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


@router.callback_query(F.data.startswith("time_"))
async def select_time(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split("_")
        date_str = parts[1]
        time_str = parts[2]
        master_id = int(parts[3])
        
        selected_time = datetime.strptime(time_str, "%H:%M").time()
        selected_date = date.fromisoformat(date_str)
        
        await state.update_data(time=time_str, selected_time=selected_time, selected_date=selected_date, master_id=master_id)
        
        data = await state.get_data()
        
        if "service_id" not in data:
            await callback.message.edit_text(
                "❌ Ошибка: данные записи потеряны. Начните заново.",
                reply_markup=get_main_menu()
            )
            await callback.answer()
            return
        
        db = next(get_db())
        services = get_services(db)
        service = next((s for s in services if s.id == data["service_id"]), None)
        masters = get_masters(db)
        master = next((m for m in masters if m.id == data.get("master_id", master_id)), None)
        db.close()
        
        if not service or not master:
            await callback.message.edit_text(
                "❌ Ошибка: услуга или мастер не найдены.",
                reply_markup=get_main_menu()
            )
            await callback.answer()
            return
        
        confirmation_text = (
            f"📋 Подтверждение записи:\n\n"
            f"✨ Услуга: {service.name}\n"
            f"💰 Цена: {service.price} ₽\n"
            f"👤 Мастер: {master.name}\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}\n\n"
            f"Подтвердить запись?"
        )
        
        keyboard = get_booking_confirmation(service, master, date_str, time_str)
        
        await callback.message.edit_text(confirmation_text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Произошла ошибка: {str(e)}\nПопробуйте начать заново /start",
            reply_markup=get_main_menu()
        )
        await callback.answer()


@router.callback_query(F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        
        required_fields = ["service_id", "master_id", "selected_date", "selected_time", "service_name", "master_name", "date", "time"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            await callback.message.edit_text(
                f"❌ Ошибка: отсутствуют данные {missing}. Начните заново /start",
                reply_markup=get_main_menu()
            )
            await callback.answer()
            await state.clear()
            return
        
        user = callback.from_user
        
        db = next(get_db())
        booking, error = create_booking(
            db=db,
            user_id=user.id,
            username=user.username,
            full_name=user.full_name or user.first_name,
            service_id=data["service_id"],
            master_id=data["master_id"],
            date_val=data["selected_date"],
            time_val=data["selected_time"]
        )
        db.close()
        
        if error:
            await callback.message.edit_text(f"❌ {error}", reply_markup=get_main_menu())
        else:
            await callback.message.edit_text(
                f"✅ Запись оформлена!\n\n"
                f"✨ Услуга: {data['service_name']}\n"
                f"👤 Мастер: {data['master_name']}\n"
                f"📅 Дата: {data['date']}\n"
                f"🕐 Время: {data['time']}\n\n"
                f"Мы свяжемся с вами для подтверждения.",
                reply_markup=get_main_menu()
            )
            
            for admin_id in config.ADMIN_IDS:
                try:
                    await callback.bot.send_message(
                        admin_id,
                        f"🔔 Новая запись!\n\n"
                        f"👤 Клиент: @{user.username or user.first_name}\n"
                        f"✨ Услуга: {data['service_name']}\n"
                        f"👤 Мастер: {data['master_name']}\n"
                        f"📅 Дата: {data['date']}\n"
                        f"🕐 Время: {data['time']}"
                    )
                except:
                    pass
        
        await state.clear()
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при записи: {str(e)}\nПопробуйте начать заново /start",
            reply_markup=get_main_menu()
        )
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
    db = next(get_db())
    bookings = get_user_bookings(db, callback.from_user.id)
    db.close()
    
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
    
    await callback.answer()


@router.callback_query(F.data.startswith("booking_detail_"))
async def booking_detail(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[2])
    db = next(get_db())
    bookings = get_user_bookings(db, callback.from_user.id)
    booking = next((b for b in bookings if b.id == booking_id), None)
    db.close()
    
    if not booking:
        await callback.answer("Запись не найдена")
        return
    
    status = "⏳ Ожидает подтверждения" if booking.status == "pending" else "✅ Подтверждена"
    
    text = (
        f"📋 Запись #{booking.id}\n\n"
        f"Статус: {status}\n"
        f"✨ Услуга: {booking.service.name}\n"
        f"💰 Цена: {booking.service.price} ₽\n"
        f"👤 Мастер: {booking.master.name}\n"
        f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
        f"🕐 Время: {booking.time.strftime('%H:%M')}"
    )
    
    await callback.message.edit_text(text, reply_markup=get_booking_detail_keyboard(booking_id))
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_"))
async def cancel_user_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[1])
    
    db = next(get_db())
    success = cancel_booking(db, booking_id)
    db.close()
    
    if success:
        await callback.message.edit_text(
            "❌ Запись отменена.",
            reply_markup=get_back_to_bookings()
        )
    else:
        await callback.answer("Не удалось отменить запись")
    
    await callback.answer()


@router.callback_query(F.data.startswith("reschedule_"))
async def reschedule_booking_start(callback: CallbackQuery, state: FSMContext):
    booking_id = int(callback.data.split("_")[1])
    
    await state.update_data(booking_id=booking_id)
    await state.set_state(RescheduleState.new_date)
    
    await callback.message.edit_text(
        "📅 Выберите новую дату:",
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
        f"📱 @{config.ADMIN_USERNAME}\n"
        f"📞 {config.ADMIN_PHONE}\n"
        "📍 Адрес: ул. Примерная, д. 1",
        reply_markup=get_contacts_keyboard()
    )
    await callback.answer()

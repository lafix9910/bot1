from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config


def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Записаться", callback_data="book_appointment")],
        [InlineKeyboardButton(text="📋 Мои записи", callback_data="my_bookings")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])


def get_services_keyboard(services: list):
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.button(
            text=f"{service.name} — {service.price} ₽",
            callback_data=f"service_{service.id}"
        )
    builder.button(text="◀️ Назад", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


def get_masters_keyboard(masters: list):
    builder = InlineKeyboardBuilder()
    for master in masters:
        builder.button(
            text=f"👤 {master.name}",
            callback_data=f"master_{master.id}"
        )
    builder.button(text="◀️ Назад", callback_data="back_services")
    builder.adjust(1)
    return builder.as_markup()


def get_time_slots_keyboard(slots: list, date_str: str, master_id: int):
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(
            text=f"{slot.strftime('%H:%M')}",
            callback_data=f"time_{date_str}_{slot.strftime('%H:%M')}_{master_id}"
        )
    builder.button(text="◀️ Назад", callback_data=f"master_{master_id}")
    builder.adjust(3)
    return builder.as_markup()


def get_booking_confirmation(date_str: str, time_str: str, master_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{date_str}_{time_str}_{master_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_booking")]
    ])


def get_my_bookings_keyboard(bookings: list):
    builder = InlineKeyboardBuilder()
    for booking in bookings:
        status_emoji = "⏳" if booking.status == "pending" else "✅"
        builder.button(
            text=f"{status_emoji} {booking.date.strftime('%d.%m.%Y')} {booking.time.strftime('%H:%M')} — {booking.service.name}",
            callback_data=f"booking_detail_{booking.id}"
        )
    builder.button(text="◀️ Назад", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


def get_booking_detail_keyboard(booking_id: int, is_admin: bool = False, admin_id: int = None):
    """Кнопки для карточки записи. is_admin=True - для админа"""
    if is_admin:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Написать клиенту", callback_data=f"admin_write_{booking_id}")],
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{booking_id}")],
            [InlineKeyboardButton(text="🔄 Изменить время", callback_data=f"admin_edit_time_{booking_id}")],
            [InlineKeyboardButton(text="💅 Изменить услугу", callback_data=f"admin_edit_service_{booking_id}")],
            [InlineKeyboardButton(text="❌ Удалить запись", callback_data=f"admin_delete_{booking_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_bookings")]
        ])
    else:
        # Кнопка "Связаться с админом" - открывает чат с админом
        if admin_id is None and config.ADMIN_IDS:
            admin_id = config.ADMIN_IDS[0]
        
        if admin_id:
            contact_url = f"tg://user?id={admin_id}"
            contact_button = InlineKeyboardButton(text="📱 Связаться с админом", url=contact_url)
        else:
            contact_button = InlineKeyboardButton(text="📱 Связаться", callback_data=f"client_contact_{booking_id}")
        
        return InlineKeyboardMarkup(inline_keyboard=[
            [contact_button],
            [InlineKeyboardButton(text="🔄 Изменить время", callback_data=f"reschedule_{booking_id}")],
            [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_{booking_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="my_bookings")]
        ])


def get_booking_card_text(booking, show_full_info: bool = True):
    """Создать текст карточки записи"""
    status = "⏳ Ожидает" if booking.status == "pending" else "✅ Подтверждена" if booking.status == "confirmed" else "❌ Отменена"
    
    text = (
        f"📋 Запись №{booking.id}\n\n"
        f"🕓 Статус: {status}\n\n"
        f"👤 Имя: {booking.name or 'Не указано'}\n"
        f"📱 Телефон: {booking.phone or 'Не указан'}\n"
        f"🔗 Username: @{booking.username or 'Нет'}\n\n"
        f"💅 Услуга: {booking.service.name}\n"
        f"💰 Цена: {booking.service.price} ₽\n"
        f"👩‍🎨 Мастер: {booking.master.name}\n\n"
        f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
        f"🕐 Время: {booking.time.strftime('%H:%M')}\n"
    )
    
    if show_full_info and booking.comment:
        text += f"\n💬 Комментарий: {booking.comment}\n"
    
    text += f"\n🕓 Создано: {booking.created_at.strftime('%d.%m.%Y %H:%M')}"
    
    return text


def get_client_booking_card_text(booking):
    """Текст карточки для клиента"""
    status = "⏳ Ожидает подтверждения" if booking.status == "pending" else "✅ Подтверждена"
    
    text = (
        f"📋 Запись №{booking.id}\n"
        f"Статус: {status}\n\n"
        f"💅 {booking.service.name}\n"
        f"👩‍🎨 Мастер: {booking.master.name}\n"
        f"📅 {booking.date.strftime('%d.%m.%Y')}\n"
        f"🕐 {booking.time.strftime('%H:%M')}"
    )
    
    return text


def get_back_to_bookings():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ К моим записям", callback_data="my_bookings")]
    ])


def get_back_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_main")]
    ])


def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_booking")]
    ])


def get_help_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_main")]
    ])


def get_contacts_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Написать мастеру", url="https://t.me/username")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_main")]
    ])


def get_admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Все записи", callback_data="admin_bookings")],
        [InlineKeyboardButton(text="✨ Управление услугами", callback_data="admin_manage_services")],
        [InlineKeyboardButton(text="👥 Управление мастерами", callback_data="admin_manage_masters")],
        [InlineKeyboardButton(text="📅 Управление датами", callback_data="admin_dates")],
        [InlineKeyboardButton(text="🔧 Настройки рабочих часов", callback_data="admin_hours")],
        [InlineKeyboardButton(text="◀️ Выход", callback_data="back_main")]
    ])


def get_admin_bookings_keyboard(bookings: list):
    builder = InlineKeyboardBuilder()
    for booking in bookings:
        status_icon = "⏳" if booking.status == "pending" else "✅" if booking.status == "confirmed" else "❌"
        text = f"{status_icon} @{booking.username or booking.full_name or 'Unknown'} | {booking.date.strftime('%d.%m')} {booking.time.strftime('%H:%M')} | {booking.service.name}"
        builder.button(
            text=text,
            callback_data=f"admin_booking_{booking.id}"
        )
    builder.button(text="◀️ Админ-меню", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_booking_actions(booking_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{booking_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin_cancel_{booking_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_bookings")]
    ])


def get_masters_management_keyboard(masters: list):
    builder = InlineKeyboardBuilder()
    for master in masters:
        builder.button(
            text=f"❌ {master.name}",
            callback_data=f"admin_delete_master_{master.id}"
        )
    builder.button(text="➕ Добавить мастера", callback_data="admin_add_master")
    builder.button(text="◀️ Админ-меню", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_services_management_keyboard(services: list):
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.button(
            text=f"❌ {service.name} — {service.price} ₽",
            callback_data=f"admin_delete_service_{service.id}"
        )
    builder.button(text="➕ Добавить услугу", callback_data="admin_add_service")
    builder.button(text="◀️ Админ-меню", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import Service, Master


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


def get_booking_confirmation(service: Service, master: Master, date_str: str, time_str: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_booking")],
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


def get_booking_detail_keyboard(booking_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перенести", callback_data=f"reschedule_{booking_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{booking_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="my_bookings")]
    ])


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
        [InlineKeyboardButton(text="📅 Управление датами", callback_data="admin_dates")],
        [InlineKeyboardButton(text="👥 Добавить мастера", callback_data="admin_add_master")],
        [InlineKeyboardButton(text="🔧 Настройки рабочих часов", callback_data="admin_hours")],
        [InlineKeyboardButton(text="◀️ Выход", callback_data="back_main")]
    ])


def get_admin_bookings_keyboard(bookings: list):
    builder = InlineKeyboardBuilder()
    for booking in bookings:
        builder.button(
            text=f"@{booking.username or 'Unknown'} | {booking.date.strftime('%d.%m')} {booking.time.strftime('%H:%M')} | {booking.service.name}",
            callback_data=f"admin_booking_{booking.id}"
        )
    builder.button(text="◀️ Админ-меню", callback_data="admin_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_booking_actions(booking_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{booking_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin_cancel_{booking_id}")],
        [InlineKeyboardButton(text="🔄 Перенести", callback_data=f"admin_reschedule_{booking_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_bookings")]
    ])

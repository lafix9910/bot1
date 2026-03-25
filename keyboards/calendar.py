from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta
from config import DAYS_IN_ADVANCE


def get_calendar_keyboard(master_id: int):
    builder = InlineKeyboardBuilder()
    
    today = date.today()
    dates = [today + timedelta(days=i) for i in range(DAYS_IN_ADVANCE)]
    
    row = []
    for i, d in enumerate(dates):
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_name = day_names[d.weekday()]
        
        if d.weekday() >= 5:
            continue
            
        btn_text = f"{d.day}.{d.month:02d} ({day_name})"
        builder.button(
            text=btn_text,
            callback_data=f"calendar_{master_id}_{d.isoformat()}"
        )
        
        if (i + 1) % 4 == 0:
            builder.adjust(4)
    
    builder.adjust(4)
    builder.button(text="◀️ Назад", callback_data=f"master_{master_id}")
    
    return builder.as_markup()


def get_calendar_for_booking(master_id: int):
    return get_calendar_keyboard(master_id)

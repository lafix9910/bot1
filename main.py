import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from config import BOT_TOKEN
from database import init_db, add_default_data, get_db, get_services, get_masters
from handlers import client_router, admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(client_router)
dp.include_router(admin_router)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    from keyboards import get_main_menu
    await message.answer(
        "👋 Добро пожаловать в салон красоты!\n\nВыберите действие:",
        reply_markup=get_main_menu()
    )


@dp.message(Command("mybookings"))
async def cmd_mybookings(message: Message):
    from database import get_user_bookings
    from keyboards import get_my_bookings_keyboard, get_back_main
    
    db = next(get_db())
    bookings = get_user_bookings(db, message.from_user.id)
    db.close()
    
    if not bookings:
        await message.answer("📭 У вас пока нет записей.", reply_markup=get_back_main())
    else:
        text = "📋 Ваши записи:\n\n"
        for b in bookings:
            status = "⏳ Ожидает" if b.status == "pending" else "✅ Подтверждена"
            text += f"{status}\n"
            text += f"✨ {b.service.name}\n"
            text += f"👤 {b.master.name}\n"
            text += f"📅 {b.date.strftime('%d.%m.%Y')} {b.time.strftime('%H:%M')}\n\n"
        
        await message.answer(text, reply_markup=get_my_bookings_keyboard(bookings))


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    from keyboards import get_admin_menu
    from handlers.admin import is_admin
    
    if not is_admin(message.from_user.id, message.from_user.username):
        await message.answer("⛔ Доступ запрещён")
        return
    
    await message.answer("🔧 Админ-панель:", reply_markup=get_admin_menu())


async def main():
    logger.info("Initializing database...")
    init_db()
    
    db = next(get_db())
    services = get_services(db)
    masters = get_masters(db)
    
    if not services or not masters:
        logger.info("Adding default data...")
        add_default_data(db)
    
    db.close()
    
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

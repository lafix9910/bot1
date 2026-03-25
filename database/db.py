from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, Service, Master, Booking, MasterSchedule, TimeSlot
from datetime import date, time, datetime, timedelta
from config import DATABASE_URL, WORKING_HOURS_START, WORKING_HOURS_END, SLOT_DURATION_MINUTES, DAYS_IN_ADVANCE
import config
import logging

logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_service(db, name, price, description=None, duration=60):
    service = db.query(Service).filter(Service.name == name).first()
    if not service:
        service = Service(name=name, price=price, description=description, duration_minutes=duration)
        db.add(service)
        db.commit()
        db.refresh(service)
    return service


def get_or_create_master(db, name, username=None, bio=None):
    master = db.query(Master).filter(Master.name == name).first()
    if not master:
        master = Master(name=name, username=username, bio=bio)
        db.add(master)
        db.commit()
        db.refresh(master)
    return master


def get_services(db):
    return db.query(Service).filter(Service.is_active == True).all()


def get_masters(db):
    return db.query(Master).filter(Master.is_active == True).all()


def get_available_slots(db, master_id, selected_date: date):
    booked_slots = db.query(TimeSlot).filter(
        TimeSlot.master_id == master_id,
        TimeSlot.date == selected_date,
        TimeSlot.is_booked == True
    ).all()
    
    booked_times = {slot.time for slot in booked_slots}
    
    all_slots = []
    current_time = time(WORKING_HOURS_START, 0)
    end_time = time(WORKING_HOURS_END, 0)
    
    while current_time < end_time:
        if current_time not in booked_times:
            all_slots.append(current_time)
        current_time = (datetime.combine(date.today(), current_time) + timedelta(minutes=SLOT_DURATION_MINUTES)).time()
    
    return all_slots


def create_booking(db, user_id, username, name, phone, service_id, master_id, date_val, time_val, comment=None):
    """Создать новую запись с полными данными клиента"""
    logger.info(f"Creating booking: user_id={user_id}, name={name}, phone={phone}, service_id={service_id}, master_id={master_id}, date={date_val}, time={time_val}")
    
    # Проверяем, нет ли уже записи на это время у этого мастера
    existing_booking = db.query(Booking).filter(
        Booking.master_id == master_id,
        Booking.date == date_val,
        Booking.time == time_val,
        Booking.status.in_(["pending", "confirmed"])
    ).first()
    
    if existing_booking:
        logger.warning(f"Booking already exists for master {master_id} at {date_val} {time_val}")
        return None, "Это время уже занято. Пожалуйста, выберите другое."
    
    # Проверяем, есть ли уже запись у этого пользователя на это время
    user_booking = db.query(Booking).filter(
        Booking.user_id == int(user_id),
        Booking.date == date_val,
        Booking.time == time_val,
        Booking.status.in_(["pending", "confirmed"])
    ).first()
    
    if user_booking:
        logger.warning(f"User {user_id} already has booking at {date_val} {time_val}")
        return None, "У вас уже есть запись на это время"
    
    # Создаём новую запись
    booking = Booking(
        user_id=int(user_id),
        username=username,
        name=name,
        phone=phone,
        comment=comment,
        service_id=service_id,
        master_id=master_id,
        date=date_val,
        time=time_val,
        status="pending"
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    logger.info(f"Booking created with id={booking.id}")
    
    # Блокируем слот
    time_slot = db.query(TimeSlot).filter(
        TimeSlot.master_id == master_id,
        TimeSlot.date == date_val,
        TimeSlot.time == time_val
    ).first()
    
    if not time_slot:
        time_slot = TimeSlot(master_id=master_id, date=date_val, time=time_val)
        db.add(time_slot)
    
    time_slot.is_booked = True
    time_slot.booking_id = booking.id
    db.commit()
    
    return booking, None


def cancel_booking(db, booking_id):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        return False, None
    
    user_id = booking.user_id
    name = booking.name
    
    time_slot = db.query(TimeSlot).filter(
        TimeSlot.master_id == booking.master_id,
        TimeSlot.date == booking.date,
        TimeSlot.time == booking.time
    ).first()
    
    if time_slot:
        time_slot.is_booked = False
        time_slot.booking_id = None
    
    booking.status = "cancelled"
    db.commit()
    logger.info(f"Booking {booking_id} cancelled")
    return True, {"user_id": user_id, "name": name}


def confirm_booking(db, booking_id):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        return False, None
    
    user_id = booking.user_id
    name = booking.name
    
    booking.status = "confirmed"
    db.commit()
    logger.info(f"Booking {booking_id} confirmed")
    return True, {"user_id": user_id, "name": name}


def get_booking_by_id(db, booking_id):
    return db.query(Booking).filter(Booking.id == booking_id).first()


def reschedule_booking(db, booking_id, new_date, new_time):
    """Изменить время записи"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        return False, "Запись не найдена", None
    
    existing = db.query(Booking).filter(
        Booking.master_id == booking.master_id,
        Booking.date == new_date,
        Booking.time == new_time,
        Booking.status.in_(["pending", "confirmed"]),
        Booking.id != booking_id
    ).first()
    
    if existing:
        return False, "Это время уже занято", None
    
    old_slot = db.query(TimeSlot).filter(
        TimeSlot.master_id == booking.master_id,
        TimeSlot.date == booking.date,
        TimeSlot.time == booking.time
    ).first()
    
    if old_slot:
        old_slot.is_booked = False
        old_slot.booking_id = None
    
    new_slot = db.query(TimeSlot).filter(
        TimeSlot.master_id == booking.master_id,
        TimeSlot.date == new_date,
        TimeSlot.time == new_time
    ).first()
    
    if not new_slot:
        new_slot = TimeSlot(master_id=booking.master_id, date=new_date, time=new_time)
        db.add(new_slot)
    
    new_slot.is_booked = True
    new_slot.booking_id = booking.id
    
    old_date = booking.date
    old_time = booking.time
    booking.date = new_date
    booking.time = new_time
    booking.status = "pending"
    db.commit()
    
    logger.info(f"Booking {booking_id} rescheduled: {old_date} {old_time} -> {new_date} {new_time}")
    
    return True, None, {"user_id": booking.user_id, "name": booking.name, "old_date": old_date, "old_time": old_time}


def update_booking_service(db, booking_id, new_service_id):
    """Изменить услугу в записи (для админа)"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        return False, "Запись не найдена", None
    
    old_service = booking.service_id
    booking.service_id = new_service_id
    db.commit()
    
    logger.info(f"Booking {booking_id} service changed: {old_service} -> {new_service_id}")
    
    return True, None, {"user_id": booking.user_id, "name": booking.name}


def delete_booking(db, booking_id):
    """Удалить запись из базы"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        return False, "Запись не найдена"
    
    user_id = booking.user_id
    name = booking.name
    
    # Освобождаем слот
    time_slot = db.query(TimeSlot).filter(
        TimeSlot.master_id == booking.master_id,
        TimeSlot.date == booking.date,
        TimeSlot.time == booking.time
    ).first()
    
    if time_slot:
        time_slot.is_booked = False
        time_slot.booking_id = None
    
    # Удаляем запись
    db.delete(booking)
    db.commit()
    
    logger.info(f"Booking {booking_id} deleted")
    
    return True, {"user_id": user_id, "name": name}


def get_user_bookings(db, user_id):
    """Получить записи пользователя по user_id (telegram id)"""
    logger.info(f"Getting user bookings for user_id={user_id}, type={type(user_id)}")
    
    bookings = db.query(Booking).filter(
        Booking.user_id == int(user_id),
        Booking.status.in_(["pending", "confirmed"])
    ).order_by(Booking.date, Booking.time).all()
    
    logger.info(f"Found {len(bookings)} bookings for user {user_id}")
    return bookings


def get_all_bookings(db, status=None):
    """Получить все записи (для админа)"""
    logger.info(f"Getting all bookings, status filter: {status}")
    
    query = db.query(Booking)
    if status:
        query = query.filter(Booking.status == status)
    
    bookings = query.order_by(Booking.date, Booking.time).all()
    logger.info(f"Found {len(bookings)} total bookings")
    return bookings


def add_default_data(db):
    services = [
        ("Маникюр", 1500, "Классический маникюр с покрытием", 60),
        ("Педикюр", 2000, "Классический педикюр", 60),
        ("Дизайн", 500, "Дизайн ногтей (за один ноготь)", 30),
        ("Маникюр + Педикюр", 3000, "Комплексная процедура", 120),
        ("Снятие покрытия", 300, "Снятие старого лака/гель-лака", 20),
    ]
    
    for name, price, desc, duration in services:
        get_or_create_service(db, name, price, desc, duration)
    
    masters = [
        ("Анна", "anna_nails", "Специалист по маникюру с 5-летним опытом"),
        ("Мария", "maria_nails", "Мастер педикюра и дизайна"),
        ("Елена", "elena_nails", "Топ-мастер по всем видам услуг"),
    ]
    
    for name, username, bio in masters:
        get_or_create_master(db, name, username, bio)
    
    db.commit()


def delete_master(db, master_id):
    master = db.query(Master).filter(Master.id == master_id).first()
    if not master:
        return False
    master.is_active = False
    db.commit()
    return True


def get_master_by_id(db, master_id):
    return db.query(Master).filter(Master.id == master_id).first()


def delete_service(db, service_id):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        return False
    service.is_active = False
    db.commit()
    return True


def get_service_by_id(db, service_id):
    return db.query(Service).filter(Service.id == service_id).first()


def create_service(db, name, price, description=None, duration=60):
    service = Service(name=name, price=price, description=description, duration_minutes=duration, is_active=True)
    db.add(service)
    db.commit()
    db.refresh(service)
    return service

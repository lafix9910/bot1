from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, Service, Master, Booking, MasterSchedule, TimeSlot
from datetime import date, time, datetime, timedelta
from config import DATABASE_URL, WORKING_HOURS_START, WORKING_HOURS_END, SLOT_DURATION_MINUTES, DAYS_IN_ADVANCE
import config

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


def create_booking(db, user_id, username, full_name, service_id, master_id, date_val, time_val, phone=None):
    existing_booking = db.query(Booking).filter(
        Booking.user_id == user_id,
        Booking.date == date_val,
        Booking.time == time_val,
        Booking.status.in_(["pending", "confirmed"])
    ).first()
    
    if existing_booking:
        return None, "У вас уже есть запись на это время"
    
    booking = Booking(
        user_id=user_id,
        username=username,
        full_name=full_name,
        phone=phone,
        service_id=service_id,
        master_id=master_id,
        date=date_val,
        time=time_val,
        status="pending"
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
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
        return False
    
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
    return True


def confirm_booking(db, booking_id):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        return False
    
    booking.status = "confirmed"
    db.commit()
    return True


def reschedule_booking(db, booking_id, new_date, new_time):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        return False, "Запись не найдена"
    
    existing = db.query(Booking).filter(
        Booking.master_id == booking.master_id,
        Booking.date == new_date,
        Booking.time == new_time,
        Booking.status.in_(["pending", "confirmed"]),
        Booking.id != booking_id
    ).first()
    
    if existing:
        return False, "Это время уже занято"
    
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
    
    booking.date = new_date
    booking.time = new_time
    booking.status = "pending"
    db.commit()
    
    return True, None


def get_user_bookings(db, user_id):
    return db.query(Booking).filter(
        Booking.user_id == user_id,
        Booking.status.in_(["pending", "confirmed"])
    ).order_by(Booking.date, Booking.time).all()


def get_all_bookings(db, status=None):
    query = db.query(Booking)
    if status:
        query = query.filter(Booking.status == status)
    return query.order_by(Booking.date, Booking.time).all()


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

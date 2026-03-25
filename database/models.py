from sqlalchemy import Column, Integer, String, Date, Time, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    
    bookings = relationship("Booking", back_populates="service")


class Master(Base):
    __tablename__ = "masters"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    username = Column(String(100))
    bio = Column(Text)
    is_active = Column(Boolean, default=True)
    
    bookings = relationship("Booking", back_populates="master")
    schedules = relationship("MasterSchedule", back_populates="master")


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String(100))
    name = Column(String(100))
    phone = Column(String(20))
    comment = Column(Text)
    
    service_id = Column(Integer, ForeignKey("services.id"))
    master_id = Column(Integer, ForeignKey("masters.id"))
    
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    
    status = Column(String(20), default="pending")
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    service = relationship("Service", back_populates="bookings")
    master = relationship("Master", back_populates="bookings")


class MasterSchedule(Base):
    __tablename__ = "master_schedules"
    
    id = Column(Integer, primary_key=True)
    master_id = Column(Integer, ForeignKey("masters.id"))
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_working = Column(Boolean, default=True)
    
    master = relationship("Master", back_populates="schedules")


class TimeSlot(Base):
    __tablename__ = "time_slots"
    
    id = Column(Integer, primary_key=True)
    master_id = Column(Integer, ForeignKey("masters.id"))
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    is_booked = Column(Boolean, default=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)

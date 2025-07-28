# app/database/models.py
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(BigInteger, primary_key=True, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    registration_date = Column(DateTime, default=datetime.now)

    bookings = relationship("Booking", back_populates="user")


class Service(Base):
    __tablename__ = 'services'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    price = Column(Integer, nullable=False)
    description = Column(String)
    duration_hours = Column(Integer)

    bookings = relationship("Booking", back_populates="service") # <-- ВОССТАНОВЛЕНО: это свойство было потеряно


class Barber(Base):
    __tablename__ = 'barbers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)

    bookings = relationship("Booking", back_populates="barber")


class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    barber_id = Column(Integer, ForeignKey('barbers.id'), nullable=True)
    booking_date = Column(DateTime, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="bookings")
    service = relationship("Service", back_populates="bookings") # Это требует 'bookings' на Service
    barber = relationship("Barber", back_populates="bookings")


class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), unique=True, nullable=False)
    appointed_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
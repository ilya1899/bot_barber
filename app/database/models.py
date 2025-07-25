from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, unique=True, autoincrement=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    registration_date = Column(DateTime, default=datetime.now)

    bookings = relationship("Booking", back_populates="user")

class Service(Base):
    __tablename__ = 'services'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Integer, nullable=False)

class Barber(Base):
    __tablename__ = 'barbers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    bookings = relationship("Booking", back_populates="barber")

class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    barber_id = Column(Integer, ForeignKey('barbers.id'), nullable=True)
    booking_date = Column(DateTime, nullable=False)
    status = Column(String, default="pending")

    user = relationship("User", back_populates="bookings")
    service = relationship("Service")
    barber = relationship("Barber", back_populates="bookings")
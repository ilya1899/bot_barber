# app/database/models.py
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Table, Date # Добавляем Date
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func # Импортируем func для func.now()

Base = declarative_base()

# Промежуточная таблица для связи многие-ко-многим между Barber и Service
barber_service_association_table = Table(
    'barber_service_association', Base.metadata,
    Column('barber_id', Integer, ForeignKey('barbers.id'), primary_key=True),
    Column('service_id', Integer, ForeignKey('services.id'), primary_key=True)
)

class User(Base):
    __tablename__ = 'users'
    user_id = Column(BigInteger, primary_key=True, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    registration_date = Column(DateTime, default=func.now()) # ИСПРАВЛЕНО: func.now()

    bookings = relationship("Booking", back_populates="user")


class Service(Base):
    __tablename__ = 'services'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    price = Column(Integer, nullable=False)
    description = Column(String)
    duration_hours = Column(Integer)

    bookings = relationship("Booking", back_populates="service")
    barbers = relationship("Barber", secondary=barber_service_association_table, back_populates="services")


class Barber(Base):
    __tablename__ = 'barbers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    photo_id = Column(String, nullable=True)

    bookings = relationship("Booking", back_populates="barber")
    services = relationship("Service", secondary=barber_service_association_table, back_populates="barbers")


class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    barber_id = Column(Integer, ForeignKey('barbers.id'), nullable=True)
    booking_date = Column(DateTime, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=func.now()) # ИСПРАВЛЕНО: func.now()

    user = relationship("User", back_populates="bookings")
    service = relationship("Service", back_populates="bookings")
    barber = relationship("Barber", back_populates="bookings")


class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), unique=True, nullable=False)
    appointed_at = Column(DateTime, default=func.now()) # ИСПРАВЛЕНО: func.now()

    user = relationship("User")

# New model for Barber Vacation (one-to-many relationship with Barber)
class BarberVacation(Base):
    __tablename__ = 'barber_vacations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    barber_id = Column(Integer, ForeignKey('barbers.id'), nullable=False)
    start_date = Column(Date, nullable=False) # ИСПРАВЛЕНО: Date вместо DateTime, т.к. это даты
    end_date = Column(Date, nullable=False)   # ИСПРАВЛЕНО: Date вместо DateTime
    created_at = Column(DateTime, default=func.now()) # ИСПРАВЛЕНО: func.now()

    barber = relationship("Barber") # Relationship to the Barber model
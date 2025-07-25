from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.database.models import User, Service, Barber, Booking
from datetime import datetime



async def add_user(session: AsyncSession, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> User:
    async with session.begin():
        user = await session.scalar(select(User).where(User.id == user_id))
        if not user:
            new_user = User(id=user_id, username=username, first_name=first_name, last_name=last_name)
            session.add(new_user)
            await session.commit()
            return new_user
        return user

async def get_user(session: AsyncSession, user_id: int) -> User | None:
    async with session.begin():
        user = await session.scalar(select(User).where(User.id == user_id))
        return user

async def update_user_phone(session: AsyncSession, user_id: int, phone_number: str) -> bool:
    async with session.begin():
        user = await session.scalar(select(User).where(User.id == user_id))
        if user:
            user.phone_number = phone_number
            await session.commit()
            return True
        return False

async def update_user_name(session: AsyncSession, user_id: int, first_name: str) -> bool:
    async with session.begin():
        user = await session.scalar(select(User).where(User.id == user_id))
        if user:
            user.first_name = first_name
            await session.commit()
            return True
        return False

async def add_service(session: AsyncSession, name: str, price: int, description: str = None) -> Service:
    async with session.begin():
        new_service = Service(name=name, price=price, description=description)
        session.add(new_service)
        await session.commit()
        return new_service

async def get_services(session: AsyncSession) -> list[Service]:
    async with session.begin():
        result = await session.scalars(select(Service))
        return result.all()

async def get_service_by_id(session: AsyncSession, service_id: int) -> Service | None:
    async with session.begin():
        service = await session.scalar(select(Service).where(Service.id == service_id))
        return service

async def add_barber(session: AsyncSession, name: str, description: str = None) -> Barber:
    async with session.begin():
        new_barber = Barber(name=name, description=description)
        session.add(new_barber)
        await session.commit()
        return new_barber

async def get_barbers(session: AsyncSession) -> list[Barber]:
    async with session.begin():
        result = await session.scalars(select(Barber))
        return result.all()

async def get_barber_by_id(session: AsyncSession, barber_id: int) -> Barber | None:
    async with session.begin():
        barber = await session.scalar(select(Barber).where(Barber.id == barber_id))
        return barber

async def create_booking(session: AsyncSession, user_id: int, service_id: int, booking_date: datetime, barber_id: int = None) -> Booking:
    async with session.begin():
        new_booking = Booking(
            user_id=user_id,
            service_id=service_id,
            barber_id=barber_id,
            booking_date=booking_date,
            status="pending"
        )
        session.add(new_booking)
        await session.commit()
        return new_booking

async def get_user_bookings(session: AsyncSession, user_id: int) -> list[Booking]:
    async with session.begin():
        result = await session.scalars(
            select(Booking)
            .where(Booking.user_id == user_id)
            .options(selectinload(Booking.service), selectinload(Booking.barber))
            .order_by(Booking.booking_date.desc())
        )
        return result.all()

async def cancel_booking(session: AsyncSession, booking_id: int) -> bool:
    async with session.begin():
        booking = await session.scalar(select(Booking).where(Booking.id == booking_id))
        if booking:
            booking.status = "cancelled"
            await session.commit()
            return True
        return False

async def get_booking_by_id(session: AsyncSession, booking_id: int) -> Booking | None:
    async with session.begin():
        booking = await session.scalar(
            select(Booking)
            .where(Booking.id == booking_id)
            .options(selectinload(Booking.service), selectinload(Booking.barber))
        )
        return booking

async def delete_booking(session: AsyncSession, booking_id: int) -> bool:
    async with session.begin():
        booking = await session.scalar(select(Booking).where(Booking.id == booking_id))
        if booking:
            await session.delete(booking)
            await session.commit()
            return True
        return False
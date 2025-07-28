from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.database.models import User, Service, Barber, Booking, Admin # Импортируем Admin
from datetime import datetime
from typing import List, Optional

async def add_user(session: AsyncSession, user_id: int, username: str, first_name: str, last_name: str) -> User:
    """Добавляет или обновляет пользователя в БД."""
    stmt = select(User).where(User.user_id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
    else:
        user = User(user_id=user_id, username=username, first_name=first_name, last_name=last_name)
        session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    """Получает пользователя по user_id."""
    stmt = select(User).where(User.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def update_user_phone(session: AsyncSession, user_id: int, phone_number: str) -> Optional[User]:
    """Обновляет номер телефона пользователя."""
    stmt = update(User).where(User.user_id == user_id).values(phone_number=phone_number).returning(User)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    await session.commit()
    return user

async def update_user_name(session: AsyncSession, user_id: int, first_name: str) -> Optional[User]:
    """Обновляет имя пользователя."""
    stmt = update(User).where(User.user_id == user_id).values(first_name=first_name).returning(User)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    await session.commit()
    return user

async def add_service(session: AsyncSession, name: str, price: int, description: str, duration_hours: int) -> Service:
    """Добавляет новую услугу."""
    service = Service(name=name, price=price, description=description, duration_hours=duration_hours)
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return service

async def get_services(session: AsyncSession) -> List[Service]:
    """Получает все услуги."""
    stmt = select(Service)
    result = await session.execute(stmt)
    return result.scalars().all()

async def get_service_by_id(session: AsyncSession, service_id: int) -> Optional[Service]:
    """Получает услугу по ID."""
    stmt = select(Service).where(Service.id == service_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def delete_service(session: AsyncSession, service_id: int) -> bool:
    """Удаляет услугу по ID."""
    stmt = delete(Service).where(Service.id == service_id)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0

async def add_barber(session: AsyncSession, name: str, description: str) -> Barber:
    """Добавляет нового мастера."""
    barber = Barber(name=name, description=description)
    session.add(barber)
    await session.commit()
    await session.refresh(barber)
    return barber

async def get_barbers(session: AsyncSession) -> List[Barber]:
    """Получает всех мастеров."""
    stmt = select(Barber)
    result = await session.execute(stmt)
    return result.scalars().all()

async def get_barber_by_id(session: AsyncSession, barber_id: int) -> Optional[Barber]:
    """Получает мастера по ID."""
    stmt = select(Barber).where(Barber.id == barber_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def create_booking(session: AsyncSession, user_id: int, service_id: int, booking_date: datetime, barber_id: Optional[int] = None) -> Booking:
    """Создает новую запись."""
    booking = Booking(
        user_id=user_id,
        service_id=service_id,
        booking_date=booking_date,
        barber_id=barber_id,
        status="active"
    )
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    await session.refresh(booking, attribute_names=['service', 'barber', 'user'])
    return booking

async def get_user_bookings(session: AsyncSession, user_id: int) -> List[Booking]:
    """Получает все записи пользователя."""
    stmt = select(Booking).where(Booking.user_id == user_id).order_by(Booking.booking_date)
    result = await session.execute(stmt)
    return result.scalars().unique().all()

async def get_booking_by_id(session: AsyncSession, booking_id: int) -> Optional[Booking]:
    """Получает запись по ID."""
    stmt = select(Booking).where(Booking.id == booking_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def cancel_booking(session: AsyncSession, booking_id: int) -> bool:
    """Отменяет запись по ID."""
    stmt = update(Booking).where(Booking.id == booking_id).values(status="cancelled")
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0

# --- Функции для модели Admin ---
async def add_admin(session: AsyncSession, user_id: int) -> Optional[Admin]:
    """Добавляет пользователя в список администраторов."""
    # Проверяем, существует ли пользователь в таблице users
    user_exists = await session.execute(select(User).where(User.user_id == user_id))
    if not user_exists.scalar_one_or_none():
        # Если пользователя нет в users, возможно, его нужно сначала зарегистрировать
        # Или просто не добавлять в админы, если его нет в основной таблице пользователей
        print(f"Пользователь с user_id {user_id} не найден в таблице users. Невозможно добавить в админы.")
        return None

    # Проверяем, не является ли уже админом
    existing_admin = await session.execute(select(Admin).where(Admin.user_id == user_id))
    if existing_admin.scalar_one_or_none():
        print(f"Пользователь {user_id} уже является администратором.")
        return existing_admin.scalar_one_or_none() # Возвращаем существующего админа

    admin = Admin(user_id=user_id)
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin

async def remove_admin(session: AsyncSession, user_id: int) -> bool:
    """Удаляет пользователя из списка администраторов."""
    stmt = delete(Admin).where(Admin.user_id == user_id)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0

async def is_user_admin(session: AsyncSession, user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    stmt = select(Admin).where(Admin.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None

async def get_all_admins(session: AsyncSession) -> List[Admin]:
    """Получает список всех администраторов."""
    stmt = select(Admin)
    result = await session.execute(stmt)
    return result.scalars().all()
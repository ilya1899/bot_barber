from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple, Callable
from sqlalchemy import func, extract
from sqlalchemy.orm import joinedload
from datetime import date, datetime, timedelta

from app.database import _async_session_factory
from app.database.models import User, Service, Barber, Booking, Admin, BarberVacation, barber_service_association_table

def initialize_db_requests(session_factory):
    global _async_session_factory
    _async_session_factory = session_factory


# --- Функции для модели User ---
async def addUser(user_id: int, username: str, firstName: str, lastName: str) -> User:
    """
    Добавляет нового пользователя или обновляет существующего в базе данных.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.username = username
            user.first_name = firstName
            user.last_name = lastName
        else:
            user = User(user_id=user_id, username=username, first_name=firstName, last_name=lastName)
            session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

async def getUser(user_id: int) -> Optional[User]:
    """
    Получает пользователя по его Telegram ID.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def updateUserPhone(user_id: int, phoneNumber: str) -> Optional[User]:
    """
    Обновляет номер телефона пользователя.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = update(User).where(User.user_id == user_id).values(phone_number=phoneNumber).returning(User)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        await session.commit()
        return user

async def updateUserName(user_id: int, firstName: str) -> Optional[User]:
    """
    Обновляет имя пользователя.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = update(User).where(User.user_id == user_id).values(first_name=firstName).returning(User)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        await session.commit()
        return user

# --- Функции для модели Service ---
async def addService(name: str, price: int, description: str, durationHours: int) -> Service:
    """
    Добавляет новую услугу в базу данных.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        service = Service(name=name, price=price, description=description, duration_hours=durationHours)
        session.add(service)
        await session.commit()
        await session.refresh(service)
        return service

async def getServices() -> List[Service]:
    """
    Получает список всех услуг из базы данных.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = select(Service)
        result = await session.execute(stmt)
        return result.scalars().all()

async def getServiceById(service_id: int) -> Optional[Service]:
    """
    Получает услугу по ее ID.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = select(Service).where(Service.id == service_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def deleteService(service_id: int) -> bool:
    """
    Удаляет услугу по ее ID.
    Возвращает True, если услуга была удалена, иначе False.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = delete(Service).where(Service.id == service_id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0

# --- Функции для модели Barber ---
import traceback, logging

logger = logging.getLogger(__name__)

from sqlalchemy.orm import selectinload

async def addBarber(session: AsyncSession, name: str, description: str, photo_id: int, service_ids: list[int]):
    new_barber = Barber(name=name, description=description, photo_id=photo_id)
    if service_ids:
        # Получаем сервисы из базы
        result = await session.execute(select(Service).where(Service.id.in_(service_ids)))
        services = result.scalars().all()
        new_barber.services.extend(services)

    session.add(new_barber)
    await session.commit()
    await session.refresh(new_barber)
    return new_barber

async def get_barber_with_services(barber_id: int):
    """
    Возвращает мастера с привязанными услугами.
    """
    async with _async_session_factory() as session:
        result = await session.execute(
            select(Barber)
            .options(selectinload(Barber.services))  # подгружаем услуги
            .where(Barber.id == barber_id)
        )
        return result.scalars().first()

async def get_busy_barbers_by_datetime(date_: date, time_: str) -> list[int]:
    # Соберём datetime из date_ и time_ (time_ в формате "HH:MM")
    booking_datetime = datetime.strptime(f"{date_} {time_}", "%Y-%m-%d %H:%M")

    async with _async_session_factory() as session:
        result = await session.execute(
            select(Booking.barber_id)
            .where(
                Booking.booking_date == booking_datetime,
                Booking.barber_id.isnot(None),
                Booking.status == "active"  # если нужно учитывать только активные записи
            )
        )
        busy_barber_ids = [row[0] for row in result.unique().all()]
    return busy_barber_ids

async def getBarbers() -> List[Barber]:
    """
    Получает список всех мастеров, жадно загружая их услуги.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = select(Barber).options(selectinload(Barber.services))
        result = await session.execute(stmt)
        return result.scalars().unique().all()

async def getBarberById(barber_id: int) -> Optional[Barber]:
    """
    Получает мастера по его ID, жадно загружая его услуги.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = select(Barber).where(Barber.id == barber_id).options(selectinload(Barber.services))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def getServicesByBarberId(barber_id: int) -> List[Service]:
    """
    Получает все услуги, предоставляемые конкретным мастером.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        barber = await session.get(Barber, barber_id, options=[selectinload(Barber.services)])
        if barber:
            return list(barber.services)
        return []

# --- Функции для модели Booking ---
async def createBooking(user_id: int, service_id: int, booking_date: datetime, barber_id: Optional[int] = None) -> Booking:
    """
    Создает новую запись на услугу.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
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

async def getUserBookings(user_id: int) -> List[Booking]:
    """
    Получает все записи для конкретного пользователя, жадно загружая связанные объекты.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = select(Booking).where(Booking.user_id == user_id).order_by(Booking.booking_date).options(
            selectinload(Booking.service),
            selectinload(Booking.barber),
            selectinload(Booking.user)
        )
        result = await session.execute(stmt)
        return result.scalars().unique().all()

async def getBookingById(booking_id: int) -> Optional[Booking]:
    """
    Получает запись по ее ID, жадно загружая связанные объекты.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = select(Booking).where(Booking.id == booking_id).options(
            selectinload(Booking.service),
            selectinload(Booking.barber),
            selectinload(Booking.user)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def cancelBooking(booking_id: int) -> bool:
    """
    Отменяет запись по ее ID.
    Возвращает True, если запись была отменена, иначе False.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = update(Booking).where(Booking.id == booking_id).values(status="cancelled")
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0


async def create_booking_entry(session_maker: Callable, user_id: int, service_id: int, chosen_date_str: str,
                               chosen_time_str: str, barber_id: int | None):
    """
    Создает запись в базе данных и возвращает результат.
    Эта функция инкапсулирует всю логику работы с сессией.
    """
    try:
        chosen_datetime = datetime.strptime(f"{chosen_date_str} {chosen_time_str}", "%Y-%m-%d %H:%M")

        async with session_maker() as session:
            user = await getUser(session, user_id)
            if not user:
                return False, "Ошибка: пользователь не найден."

            new_booking = Booking(
                service_id=service_id,
                date_time=chosen_datetime,
                user_id=user.id,
                barber_id=barber_id
            )
            session.add(new_booking)
            await session.commit()

        return True, "✅ Запись успешно создана!"

    except Exception as e:
        print(f"Ошибка при создании записи: {e}")
        return False, "❌ Произошла ошибка при создании записи."

# --- Функции для модели Admin ---
async def addAdmin(user_id: int) -> Optional[Admin]:
    """
    Добавляет пользователя в список администраторов.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        user_exists_stmt = select(User).where(User.user_id == user_id)
        user_exists_result = await session.execute(user_exists_stmt)
        if not user_exists_result.scalar_one_or_none():
            print(f"Пользователь с user_id {user_id} не найден в таблице users. Невозможно добавить в админы.")
            return None

        existing_admin_stmt = select(Admin).where(Admin.user_id == user_id)
        existing_admin_result = await session.execute(existing_admin_stmt)
        existing_admin = existing_admin_result.scalar_one_or_none()
        if existing_admin:
            print(f"Пользователь {user_id} уже является администратором.")
            return existing_admin

        admin = Admin(user_id=user_id)
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return

async def isUserAdmin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = select(Admin).where(Admin.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None


async def getNewUsersCount(start_date: Optional[date] = None, end_date: Optional[date] = None) -> int:
    """
    Возвращает количество новых пользователей за указанный период.
    Если start_date None, то считается с самого начала.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = select(func.count(User.user_id))  # ИСПРАВЛЕНО: Использовать User.user_id
        if start_date:
            stmt = stmt.where(User.registration_date >= start_date)
        if end_date:
            # Учитываем конец дня для end_date
            stmt = stmt.where(User.registration_date <= (end_date + timedelta(days=1)))

        result = await session.execute(stmt)
        return result.scalar_one()


async def getServiceBookingStatistics(start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[
    Tuple[str, int]]:
    """
    Возвращает статистику записей по услугам за указанный период.
    Возвращает список кортежей (название_услуги, количество_записей).
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = select(Service.name, func.count(Booking.id)). \
            join(Booking, Service.id == Booking.service_id)

        if start_date:
            stmt = stmt.where(Booking.booking_date >= start_date)
        if end_date:
            stmt = stmt.where(Booking.booking_date <= (end_date + timedelta(days=1)))

        stmt = stmt.group_by(Service.name).order_by(func.count(Booking.id).desc())

        result = await session.execute(stmt)
        return result.all()


async def getMasterBookingStatistics(start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[
    Tuple[str, int]]:
    """
    Возвращает статистику записей по мастерам за указанный период.
    Возвращает список кортежей (имя_мастера, количество_записей).
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        stmt = select(Barber.name, func.count(Booking.id)). \
            join(Booking, Barber.id == Booking.barber_id)

        if start_date:
            stmt = stmt.where(Booking.booking_date >= start_date)
        if end_date:
            stmt = stmt.where(Booking.booking_date <= (end_date + timedelta(days=1)))

        stmt = stmt.group_by(Barber.name).order_by(func.count(Booking.id).desc())

        result = await session.execute(stmt)
        return result.all()

async def getBookingsForDate(target_date: date) -> List[Booking]:
    """
    Получает все активные записи на конкретную дату, жадно загружая связанные услуги и мастеров.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
    async with _async_session_factory() as session:
        # Для поиска записей на конкретный день, сравниваем только дату
        # booking_date - это DateTime, поэтому нужно сравнить только компонент даты
        stmt = select(Booking).where(
            func.date(Booking.booking_date) == target_date,
            Booking.status == "active"
        ).options(
            joinedload(Booking.service), # Жадно загружаем связанную услугу
            joinedload(Booking.barber)   # Жадно загружаем связанного мастера
        ).order_by(Booking.booking_date) # Сортируем по времени записи

        result = await session.execute(stmt)
        return result.scalars().all()

async def addBooking(user_id: int, service_id: int, barber_id: Optional[int], booking_date: date, booking_time: str) -> Booking:
    """
    Создает новую запись (Booking) и сохраняет её в базе данных.
    :param user_id: ID пользователя
    :param service_id: ID услуги
    :param barber_id: ID мастера (может быть None)
    :param booking_date: Дата (date)
    :param booking_time: Время в формате HH:MM
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")

    # Объединяем дату и время
    booking_datetime = datetime.combine(
        booking_date,
        datetime.strptime(booking_time, "%H:%M").time()
    )

    async with _async_session_factory() as session:
        new_booking = Booking(
            user_id=user_id,
            service_id=service_id,
            barber_id=barber_id,
            booking_date=booking_datetime
        )
        session.add(new_booking)
        await session.commit()
        await session.refresh(new_booking)
        return new_booking


# --- Отпуск мастера ---
async def deleteBarber(barber_id: int) -> bool:
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")

    async with _async_session_factory() as session:
        # Удаляем связи мастера с услугами
        await session.execute(
            delete(barber_service_association_table).where(
                barber_service_association_table.c.barber_id == barber_id
            )
        )
        # Удаляем бронирования
        await session.execute(
            delete(Booking).where(Booking.barber_id == barber_id)
        )
        # Удаляем отпуска мастера
        await session.execute(
            delete(BarberVacation).where(BarberVacation.barber_id == barber_id)
        )
        # Удаляем самого мастера
        result = await session.execute(
            delete(Barber).where(Barber.id == barber_id)
        )

        await session.commit()
        return result.rowcount > 0


async def deleteBooking(booking_id: int) -> bool:
    """
    Полностью удаляет запись по её ID.
    Возвращает True, если запись была удалена.
    """
    if _async_session_factory is None:
        raise RuntimeError("Фабрика сессий базы данных не инициализирована.")

    async with _async_session_factory() as session:
        stmt = delete(Booking).where(Booking.id == booking_id)
        result = await session.execute(stmt)
        await session.commit()

        return result.rowcount > 0
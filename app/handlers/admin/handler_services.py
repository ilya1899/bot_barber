# app/handlers/handler_admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from app.keyboards.kbreply import main_menu_keyboard, admin_menu_keyboard
from app.keyboards.kbinline import admin_services_menu_keyboard, admin_add_service_confirm_keyboard, \
    admin_services_list_action_keyboard, admin_single_service_view_keyboard, admin_confirm_delete_service_keyboard
from app.database import requests as db_requests
from app.database.models import Service  # Для типизации
from config import BOOKINGS_PER_PAGE

admin_router = Router()


# --- Состояния для многошаговых форм администратора ---
class AdminServiceState(StatesGroup):
    """Состояния для процесса добавления и подтверждения удаления услуг."""
    addServiceWaitingForName = State()
    addServiceWaitingForCost = State()
    addServiceWaitingForDuration = State()
    addServiceConfirm = State()

    deleteServiceConfirm = State()


# --- Вход в админ-панель по команде /admin ---
@admin_router.message(Command("admin"))
async def handler_admin_command(message: Message, session_maker: callable):
    """
    Обрабатывает команду /admin.
    Проверяет права пользователя и отображает админ-паменю.
    """
    async with session_maker() as session:
        if await db_requests.is_user_admin(session, message.from_user.id):
            await message.answer("Добро пожаловать в админ-панель!", reply_markup=admin_menu_keyboard)
        else:
            await message.answer("У вас нет прав для доступа к админ-панели.")


# --- Выход из админ-панели ---
@admin_router.message(F.text == "⬅️ Выйти из админ-панели")
async def handler_exit_admin_panel(message: Message, state: FSMContext, session_maker: callable):
    """
    Обрабатывает выход из админ-панели.
    Очищает состояние и возвращает в главное меню.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, message.from_user.id):
            await message.answer("У вас нет прав для выполнения этого действия.")
            return

    await state.clear()
    await message.answer("Вы вышли из админ-панели.", reply_markup=main_menu_keyboard)


# --- Управление услугами (меню) ---
@admin_router.message(F.text == "Услуги")
async def handler_admin_services_menu(message: Message, state: FSMContext, session_maker: callable):
    """
    Отображает меню управления услугами.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, message.from_user.id):
            await message.answer("У вас нет прав для выполнения этого действия.")
            return

    await state.clear()  # Очищаем состояние при входе в меню услуг
    await message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())


# --- Назад в меню услуг (Inline-кнопка) ---
@admin_router.callback_query(F.data == "adminBackToServiceMenu")
async def handler_admin_back_to_services_menu(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Возвращает администратора в меню управления услугами.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return

    await state.clear()
    await callback.message.edit_text("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
    await callback.answer()


# --- Назад в админ-панель (Inline-кнопка) ---
@admin_router.callback_query(F.data == "adminBackToAdminMenu")
async def handler_admin_back_to_admin_menu(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Возвращает администратора в главное меню админ-панели.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return

    await state.clear()
    # ИСПРАВЛЕНИЕ: Используем callback.message.answer для отправки ReplyKeyboardMarkup
    await callback.message.answer("Добро пожаловать в админ-панель!", reply_markup=admin_menu_keyboard)
    await callback.answer()  # Отвечаем на коллбэк, чтобы убрать "часики"


# --- Добавление услуги: Шаг 1 (Название) ---
@admin_router.callback_query(F.data == "adminAddService")
async def handler_admin_add_service_start(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Начинает процесс добавления новой услуги.
    Запрашивает название услуги.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return

    await callback.message.edit_text("Введите название новой услуги:")
    await state.set_state(AdminServiceState.addServiceWaitingForName)
    await callback.answer()


@admin_router.message(AdminServiceState.addServiceWaitingForName)
async def handler_admin_add_service_name(message: Message, state: FSMContext, session_maker: callable):
    """
    Обрабатывает ввод названия услуги.
    Запрашивает стоимость услуги.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, message.from_user.id):
            await message.answer("У вас нет прав для выполнения этого действия.")
            await state.clear()
            return

    service_name = message.text.strip()
    if not service_name:
        await message.answer("Название услуги не может быть пустым. Пожалуйста, введите название:")
        return
    await state.update_data(new_service_name=service_name)
    await message.answer("Введите стоимость услуги в рублях (например, 1500):")
    await state.set_state(AdminServiceState.addServiceWaitingForCost)


# --- Добавление услуги: Шаг 2 (Стоимость) ---
@admin_router.message(AdminServiceState.addServiceWaitingForCost)
async def handler_admin_add_service_cost(message: Message, state: FSMContext, session_maker: callable):
    """
    Обрабатывает ввод стоимости услуги.
    Запрашивает длительность услуги.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, message.from_user.id):
            await message.answer("У вас нет прав для выполнения этого действия.")
            await state.clear()
            return

    try:
        service_cost = int(message.text.strip())
        if service_cost <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Стоимость должна быть положительным числом. Пожалуйста, введите корректную стоимость:")
        return
    await state.update_data(new_service_cost=service_cost)
    await message.answer("Введите целое количество часов, требующееся на услугу (например, 1 или 2):")
    await state.set_state(AdminServiceState.addServiceWaitingForDuration)


# --- Добавление услуги: Шаг 3 (Длительность) ---
@admin_router.message(AdminServiceState.addServiceWaitingForDuration)
async def handler_admin_add_service_duration(message: Message, state: FSMContext, session_maker: callable):
    """
    Обрабатывает ввод длительности услуги.
    Показывает итоговую карточку услуги для подтверждения.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, message.from_user.id):
            await message.answer("У вас нет прав для выполнения этого действия.")
            await state.clear()
            return

    try:
        service_duration = int(message.text.strip())
        if service_duration <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "Длительность должна быть положительным числом часов. Пожалуйста, введите корректную длительность:")
        return
    await state.update_data(new_service_duration=service_duration)

    user_data = await state.get_data()
    name = user_data.get('new_service_name')
    cost = user_data.get('new_service_cost')
    duration = user_data.get('new_service_duration')

    final_card_text = (
        f"<b>Итоговая карточка услуги:</b>\n\n"
        f"Название: <b>{name}</b>\n"
        f"Стоимость: <b>{cost} руб.</b>\n"
        f"Длительность: <b>{duration} час{'а' if 1 < duration < 5 else ('ов' if duration >= 5 else '')}</b>\n\n"
        f"Подтвердите добавление или отмените."
    )
    await message.answer(final_card_text, reply_markup=admin_add_service_confirm_keyboard())
    await state.set_state(AdminServiceState.addServiceConfirm)


# --- Добавление услуги: Подтверждение ---
@admin_router.callback_query(AdminServiceState.addServiceConfirm, F.data == "adminConfirmAddService")
async def handler_admin_confirm_add_service(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Подтверждает и добавляет новую услугу в БД.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return

    user_data = await state.get_data()
    name = user_data.get('new_service_name')
    cost = user_data.get('new_service_cost')
    duration = user_data.get('new_service_duration')

    async with session_maker() as session:
        try:
            description = f"Услуга '{name}' длительностью {duration} час."
            await db_requests.add_service(session, name=name, price=cost, description=description,
                                          duration_hours=duration)
            await callback.message.edit_text("✅ Услуга успешно добавлена!")
        except Exception as e:
            print(f"Ошибка при добавлении услуги: {e}")
            await callback.message.edit_text("Произошла ошибка при добавлении услуги. Пожалуйста, попробуйте позже.")
        finally:
            await state.clear()
            await callback.message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
            await callback.answer()


# --- Добавление услуги: Отмена ---
@admin_router.callback_query(AdminServiceState.addServiceConfirm, F.data == "adminCancelAddService")
async def handler_admin_cancel_add_service(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Отменяет процесс добавления услуги.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return

    await state.clear()
    await callback.message.edit_text("❌ Добавление услуги отменено.")
    await callback.message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
    await callback.answer()


# --- Просмотр услуг (без FSMState для навигации) ---
@admin_router.callback_query(F.data == "adminViewServices")
async def handler_admin_view_services_list(callback: CallbackQuery, session_maker: callable):
    """
    Отображает список всех услуг с пагинацией для просмотра.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return
        services = await db_requests.get_services(session)

    if not services:
        await callback.message.edit_text("Пока нет добавленных услуг.")
        await callback.message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
        await callback.answer()
        return

    await callback.message.edit_text(
        "Список услуг:\n\n"
        "Выберите услугу для просмотра деталей:",
        reply_markup=admin_services_list_action_keyboard(services, "adminViewService", 0, BOOKINGS_PER_PAGE)
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adminViewServicePage_"))
async def handler_admin_view_services_paginate(callback: CallbackQuery, session_maker: callable):
    """
    Обрабатывает пагинацию списка услуг для просмотра.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return
        services = await db_requests.get_services(session)

    page = int(callback.data.split("_")[1])

    await callback.message.edit_reply_markup(
        reply_markup=admin_services_list_action_keyboard(services, "adminViewService", page, BOOKINGS_PER_PAGE)
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adminViewService_"))
async def handler_admin_view_single_service(callback: CallbackQuery, session_maker: callable):
    """
    Отображает детали выбранной услуги.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return

        service_id = int(callback.data.split("_")[1])
        service = await db_requests.get_service_by_id(session, service_id)

    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        await handler_admin_view_services_list(callback, session_maker)
        return

    service_info_text = (
        f"<b>Детали услуги:</b>\n\n"
        f"Название: <b>{service.name}</b>\n"
        f"Стоимость: <b>{service.price} руб.</b>\n"
        f"Длительность: <b>{service.duration_hours} час{'а' if 1 < service.duration_hours < 5 else ('ов' if service.duration_hours >= 5 else '')}</b>\n"
        f"Описание: {service.description}\n"
    )
    await callback.message.edit_text(service_info_text, reply_markup=admin_single_service_view_keyboard(service.id))
    await callback.answer()


# --- Удаление услуги: Шаг 1 (Выбор услуги) ---
@admin_router.callback_query(F.data == "adminDeleteService")
async def handler_admin_delete_service_start(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Начинает процесс удаления услуги.
    Отображает список услуг для выбора.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return
        services = await db_requests.get_services(session)

    if not services:
        await callback.message.edit_text("Пока нет услуг для удаления.")
        await callback.message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
        await callback.answer()
        return

    await callback.message.edit_text(
        "Выберите услугу для удаления:",
        reply_markup=admin_services_list_action_keyboard(services, "adminSelectDeleteService", 0, BOOKINGS_PER_PAGE)
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adminSelectDeleteServicePage_"))
async def handler_admin_delete_services_paginate(callback: CallbackQuery, session_maker: callable):
    """
    Обрабатывает пагинацию списка услуг для удаления.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return
        services = await db_requests.get_services(session)

    page = int(callback.data.split("_")[1])

    await callback.message.edit_reply_markup(
        reply_markup=admin_services_list_action_keyboard(services, "adminSelectDeleteService", page, BOOKINGS_PER_PAGE)
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adminSelectDeleteService_"))
async def handler_admin_confirm_delete_service(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Запрашивает подтверждение удаления выбранной услуги.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return

        service_id = int(callback.data.split("_")[1])
        service = await db_requests.get_service_by_id(session, service_id)

    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        await handler_admin_delete_service_start(callback, state, session_maker)
        return

    await state.update_data(service_to_delete_id=service_id)
    await callback.message.edit_text(
        f"Вы действительно хотите удалить услугу: <b>{service.name}</b>?",
        reply_markup=admin_confirm_delete_service_keyboard(service_id)
    )
    await state.set_state(AdminServiceState.deleteServiceConfirm)
    await callback.answer()


# --- Удаление услуги: Подтверждение ---
@admin_router.callback_query(AdminServiceState.deleteServiceConfirm, F.data.startswith("adminExecuteDeleteService_"))
async def handler_admin_execute_delete_service(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Выполняет удаление услуги из БД после подтверждения.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return

    service_id = int(callback.data.split("_")[1])
    user_data = await state.get_data()
    if user_data.get('service_to_delete_id') != service_id:
        await callback.answer("Ошибка подтверждения. Пожалуйста, попробуйте снова.", show_alert=True)
        await state.clear()
        await callback.message.edit_text("Произошла ошибка. Возвращаемся в меню услуг.",
                                         reply_markup=admin_services_menu_keyboard())
        return

    async with session_maker() as session:
        success = await db_requests.delete_service(session, service_id)

    if success:
        await callback.message.edit_text("🗑️ Услуга успешно удалена.")
    else:
        await callback.message.edit_text("Произошла ошибка при удалении услуги. Возможно, услуга уже удалена.")

    await state.clear()
    await callback.message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
    await callback.answer()


# --- Обработка кнопки "Отменить" в процессе добавления/удаления (общая) ---
@admin_router.callback_query(F.data == "adminCancelAddService")
@admin_router.callback_query(F.data == "adminCancelDeleteService")
async def handler_admin_cancel_operation(callback: CallbackQuery, state: FSMContext, session_maker: callable):
    """
    Общий хэндлер для отмены текущей административной операции.
    """
    async with session_maker() as session:
        if not await db_requests.is_user_admin(session, callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
            return

    await state.clear()
    await callback.message.edit_text("Операция отменена.")
    await callback.message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
    await callback.answer()
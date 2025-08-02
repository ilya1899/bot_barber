# app/handlers/handler_admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

# Возвращаем названия клавиатур к snake_case
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
async def handlerAdminCommand(message: Message, state: FSMContext):
    """
    Обрабатывает команду /admin.
    Проверяет права пользователя и отображает админ-панель.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
        await message.answer("У вас нет прав для доступа к админ-панели.")
        return

    await message.answer("Добро пожаловать в админ-панель!", reply_markup=admin_menu_keyboard)
    await state.clear()


# --- Выход из админ-панели ---
@admin_router.message(F.text == "⬅️ Выйти из админ-панели")
async def handlerExitAdminPanel(message: Message, state: FSMContext):
    """
    Обрабатывает выход из админ-панели.
    Очищает состояние и возвращает в главное меню.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этого действия.")
        return

    await state.clear()
    await message.answer("Вы вышли из админ-панели.", reply_markup=main_menu_keyboard)


# --- Управление услугами (меню) ---
@admin_router.message(F.text == "Услуги")
async def handlerAdminServicesMenu(message: Message, state: FSMContext):
    """
    Отображает меню управления услугами.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этого действия.")
        return

    await state.clear()
    await message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())


# --- Назад в меню услуг (Inline-кнопка) ---
@admin_router.callback_query(F.data == "adminBackToServiceMenu")
async def handlerAdminBackToServicesMenu(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает администратора в меню управления услугами.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
    await callback.answer()


# --- Назад в админ-панель (Inline-кнопка) ---
@admin_router.callback_query(F.data == "adminBackToAdminMenu")
async def handlerAdminBackToAdminMenu(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает администратора в главное меню админ-панели.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text("Добро пожаловать в админ-панель!")
    await callback.message.answer("Выберите действие:", reply_markup=admin_menu_keyboard())  # вызываем функцию, чтобы получить клавиатуру
    await callback.answer()



# --- Добавление услуги: Шаг 1 (Название) ---
@admin_router.callback_query(F.data == "adminAddService")
async def handlerAdminAddServiceStart(callback: CallbackQuery, state: FSMContext):
    """
    Начинает процесс добавления новой услуги.
    Запрашивает название услуги.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await callback.message.edit_text("Введите название новой услуги:")
    await state.set_state(AdminServiceState.addServiceWaitingForName)
    await callback.answer()


@admin_router.message(AdminServiceState.addServiceWaitingForName)
async def handlerAdminAddServiceName(message: Message, state: FSMContext):
    """
    Обрабатывает ввод названия услуги.
    Запрашивает стоимость услуги.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этого действия.")
        await state.clear()
        return

    service_name = message.text.strip()
    if not service_name:
        await message.answer("Название услуги не может быть пустым. Пожалуйста, введите название:")
        return
    await state.update_data(newServiceName=service_name)
    await message.answer("Введите стоимость услуги в рублях (например, 1500):")
    await state.set_state(AdminServiceState.addServiceWaitingForCost)


# --- Добавление услуги: Шаг 2 (Стоимость) ---
@admin_router.message(AdminServiceState.addServiceWaitingForCost)
async def handlerAdminAddServiceCost(message: Message, state: FSMContext):
    """
    Обрабатывает ввод стоимости услуги.
    Запрашивает длительность услуги.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
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
    await state.update_data(newServiceCost=service_cost)
    await message.answer("Введите целое количество часов, требующееся на услугу (например, 1 или 2):")
    await state.set_state(AdminServiceState.addServiceWaitingForDuration)


# --- Добавление услуги: Шаг 3 (Длительность) ---
@admin_router.message(AdminServiceState.addServiceWaitingForDuration)
async def handlerAdminAddServiceDuration(message: Message, state: FSMContext):
    """
    Обрабатывает ввод длительности услуги.
    Показывает итоговую карточку услуги для подтверждения.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
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
    await state.update_data(newServiceDuration=service_duration)

    user_data = await state.get_data()
    name = user_data.get('newServiceName')
    cost = user_data.get('newServiceCost')
    duration = user_data.get('newServiceDuration')

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
@admin_router.callback_query(F.data == "adminConfirmAddService")
async def handlerAdminConfirmAddService(callback: CallbackQuery, state: FSMContext):
    """
    Подтверждает и добавляет новую услугу в БД.
    """
    current_state = await state.get_state()
    if current_state != AdminServiceState.addServiceConfirm:
        await callback.answer("Неверное действие. Пожалуйста, начните добавление услуги заново.", show_alert=True)
        await state.clear()
        return

    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    user_data = await state.get_data()
    name = user_data.get('newServiceName')
    cost = user_data.get('newServiceCost')
    duration = user_data.get('newServiceDuration')

    try:
        description = f"Услуга '{name}' длительностью {duration} час."
        await db_requests.addService(name=name, price=cost, description=description,
                                     durationHours=duration)
        await callback.message.edit_text("✅ Услуга успешно добавлена!")
    except Exception as e:
        print(f"Ошибка при добавлении услуги: {e}")
        await callback.message.edit_text("Произошла ошибка при добавлении услуги. Пожалуйста, попробуйте позже.")
    finally:
        await state.clear()
        await callback.message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
        await callback.answer()


# --- Добавление услуги: Отмена ---
@admin_router.callback_query(F.data == "adminCancelAddService")
async def handlerAdminCancelAddService(callback: CallbackQuery, state: FSMContext):
    """
    Отменяет процесс добавления услуги.
    """
    current_state = await state.get_state()
    if current_state != AdminServiceState.addServiceConfirm:
        await callback.answer("Неверное действие. Пожалуйста, начните добавление услуги заново.", show_alert=True)
        await state.clear()
        return

    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text("❌ Добавление услуги отменено.")
    await callback.message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
    await callback.answer()

ADMIN_SERVICES_PER_PAGE = 5

## --- Просмотр услуг ---
@admin_router.callback_query(F.data == "adminViewServices")
async def handlerAdminViewServicesList(callback: CallbackQuery, state: FSMContext):
    """
    Отображает список всех услуг с пагинацией для просмотра.
    """
    # Проверка прав администратора
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear() # Очищаем состояние FSM

    # Получаем все услуги (предполагается, что getServices() достает их все)
    # Если getServices() требует сессию, то вам нужно добавить async with _async_session_factory() as session:
    # и передавать session в getServices(session)
    services = await db_requests.getServices()

    if not services:
        await callback.message.edit_text("Пока нет добавленных услуг.")
        await callback.message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
        await callback.answer()
        return

    # Отправляем сообщение со списком услуг на первой странице
    await callback.message.edit_text(
        "Выберите услугу для просмотра деталей:",
        reply_markup=admin_services_list_action_keyboard(services, "adminViewService", 0, ADMIN_SERVICES_PER_PAGE)
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adminViewServicePage_"))
async def handlerAdminViewServicesPaginate(callback: CallbackQuery):
    """
    Обрабатывает пагинацию списка услуг для просмотра.
    """
    # Проверка прав администратора
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    # Получаем все услуги (предполагается, что getServices() достает их все)
    services = await db_requests.getServices()

    page = int(callback.data.split("_")[1]) # Получаем номер страницы из callback_data

    # Обновляем сообщение с новой страницей услуг, сохраняя текст
    await callback.message.edit_text(
        "Список услуг:\n\n"
        "Выберите услугу для просмотра деталей:",
        reply_markup=admin_services_list_action_keyboard(services, "adminViewService", page, ADMIN_SERVICES_PER_PAGE)
    )
    await callback.answer()

# Новый хэндлер для кнопки "Назад в меню услуг"
@admin_router.callback_query(F.data == "admin_back_to_services_menu")
async def handlerAdminBackToServicesMenu(callback: CallbackQuery):
    """
    Обрабатывает возврат из просмотра услуг в меню управления услугами.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return
    await callback.message.edit_text(
        "Выберите действие с услугами:",
        reply_markup=admin_services_menu_keyboard() # Возвращаем клавиатуру меню услуг
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("adminViewService_"))
async def handlerAdminViewSingleService(callback: CallbackQuery, state: FSMContext):
    """
    Отображает детали выбранной услуги.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    service_id = int(callback.data.split("_")[1])
    service = await db_requests.getServiceById(service_id)

    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        await handlerAdminViewServicesList(callback, state)
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
async def handlerAdminDeleteServiceStart(callback: CallbackQuery, state: FSMContext):
    """
    Начинает процесс удаления услуги.
    Отображает список услуг для выбора.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear()
    services = await db_requests.getServices()

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
async def handlerAdminDeleteServicesPaginate(callback: CallbackQuery):
    """
    Обрабатывает пагинацию списка услуг для удаления.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    services = await db_requests.getServices()

    page = int(callback.data.split("_")[1])

    await callback.message.edit_reply_markup(
        reply_markup=admin_services_list_action_keyboard(services, "adminSelectDeleteService", page, BOOKINGS_PER_PAGE)
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adminSelectDeleteService_"))
async def handlerAdminConfirmDeleteService(callback: CallbackQuery, state: FSMContext):
    """
    Запрашивает подтверждение удаления выбранной услуги.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    current_state = await state.get_state()
    # Проверка состояния здесь может быть более гибкой, так как пользователь мог прийти из списка услуг для удаления
    # или из другого места. Для строгой последовательности можно добавить проверку:
    # if current_state not in [None, AdminServiceState.deleteServiceConfirm]:
    #     await callback.answer("Неверное действие. Пожалуйста, начните удаление услуги заново.", show_alert=True)
    #     await state.clear()
    #     return

    service_id = int(callback.data.split("_")[1])
    service = await db_requests.getServiceById(service_id)

    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        await handlerAdminDeleteServiceStart(callback, state)
        return

    await state.update_data(serviceToDeleteId=service_id)
    await callback.message.edit_text(
        f"Вы действительно хотите удалить услугу: <b>{service.name}</b>?",
        reply_markup=admin_confirm_delete_service_keyboard(service_id)
    )
    await state.set_state(AdminServiceState.deleteServiceConfirm)
    await callback.answer()


# --- Удаление услуги: Подтверждение ---
@admin_router.callback_query(F.data.startswith("adminExecuteDeleteService_"))
async def handlerAdminExecuteDeleteService(callback: CallbackQuery, state: FSMContext):
    """
    Выполняет удаление услуги из БД после подтверждения.
    """
    current_state = await state.get_state()
    if current_state != AdminServiceState.deleteServiceConfirm:
        await callback.answer("Неверное действие. Пожалуйста, начните удаление услуги заново.", show_alert=True)
        await state.clear()
        return

    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    service_id = int(callback.data.split("_")[1])
    user_data = await state.get_data()
    if user_data.get('serviceToDeleteId') != service_id:
        await callback.answer("Ошибка подтверждения. Пожалуйста, попробуйте снова.", show_alert=True)
        await state.clear()
        await callback.message.edit_text("Произошла ошибка. Возвращаемся в меню услуг.",
                                         reply_markup=admin_services_menu_keyboard())
        return

    try:
        success = await db_requests.deleteService(service_id)
        if success:
            await callback.message.edit_text("🗑️ Услуга успешно удалена.")
        else:
            await callback.message.edit_text("Произошла ошибка при удалении услуги. Возможно, услуга уже удалена.")
    except Exception as e:
        print(f"Ошибка при удалении услуги: {e}")
        await callback.message.edit_text("Произошла ошибка при удалении услуги. Пожалуйста, попробуйте позже.")
    finally:
        await state.clear()
        await callback.message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
        await callback.answer()


# --- Обработка кнопки "Отменить" в процессе добавления/удаления (общая) ---
@admin_router.callback_query(F.data == "adminCancelAddService")
@admin_router.callback_query(F.data == "adminCancelDeleteService")
async def handlerAdminCancelOperation(callback: CallbackQuery, state: FSMContext):
    """
    Общий хэндлер для отмены текущей административной операции.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text("Операция отменена.")
    await callback.message.answer("Выберите действие с услугами:", reply_markup=admin_services_menu_keyboard())
    await callback.answer()
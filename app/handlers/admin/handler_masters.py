# app/handlers/admin/handler_masters.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date, datetime, timedelta
from typing import List, Tuple, Optional

from app.keyboards.kbreply import admin_menu_keyboard
from app.keyboards.kbinline import (
    adminMastersMenuKeyboard, adminAddMasterConfirmKeyboard,
    getMasterSelectKeyboard, adminSingleMasterViewKeyboard,
    adminConfirmDeleteMasterKeyboard, adminMasterServicesSelectionKeyboard,
    adminMasterVacationCalendarKeyboard, adminMasterVacationConfirmKeyboard
)
from app.database import requests as db_requests
from app.database.models import Barber, Service  # Для типизации
from config import BOOKINGS_PER_PAGE  # Для пагинации

admin_masters_router = Router()


# --- Состояния для многошаговых форм администратора (Мастера) ---
class AdminMasterState(StatesGroup):
    """Состояния FSM для управления мастерами (добавление, редактирование, отпуск)."""
    # Состояния для добавления мастера
    addMasterWaitingForPhoto = State()
    addMasterWaitingForFullName = State()
    addMasterWaitingForComment = State()
    addMasterChoosingServices = State()
    addMasterConfirm = State()

    # Состояния для удаления мастера
    deleteMasterConfirm = State()

    # Состояния для отпуска
    vacationChooseMaster = State()
    vacationChooseStartDate = State()
    vacationChooseEndDate = State()
    vacationConfirm = State()


# --- Главное меню мастеров ---
@admin_masters_router.message(F.text == "Мастера")
async def handlerAdminMastersMenu(message: Message, state: FSMContext):
    """
    Отображает главное меню для управления мастерами.
    Доступно из админ-панели.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этого действия.")
        return

    await state.clear()  # Очищаем любое предыдущее состояние
    await message.answer("Выберите действие с мастерами:", reply_markup=adminMastersMenuKeyboard())


# --- Назад в админ-панель (из меню мастеров) ---
@admin_masters_router.callback_query(F.data == "adminBackToAdminMenuFromMasters")
async def handlerAdminBackToAdminMenuFromMasters(callback: CallbackQuery, state: FSMContext):
    """
    Возвращает администратора в главное меню админ-панели.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text("Вы вернулись в главное меню админ-панели.")  # Удаляем инлайн-клавиатуру
    await callback.message.answer("Добро пожаловать в админ-панель!",
                                  reply_markup=admin_menu_keyboard)  # Отправляем новое сообщение с ReplyKeyboard
    await callback.answer()


# --- Добавление мастера: Шаг 1 (Фото) ---
@admin_masters_router.callback_query(F.data == "adminAddMaster")
async def handlerAdminAddMasterStart(callback: CallbackQuery, state: FSMContext):
    """
    Начинает процесс добавления нового мастера.
    Запрашивает фотографию мастера.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await callback.message.edit_text("Отправьте фото мастера в хорошем качестве:")
    await state.set_state(AdminMasterState.addMasterWaitingForPhoto)
    await callback.answer()


@admin_masters_router.message(AdminMasterState.addMasterWaitingForPhoto, F.photo)
async def handlerAdminAddMasterPhoto(message: Message, state: FSMContext):
    """
    Обрабатывает ввод фотографии для нового мастера.
    Запрашивает полное имя (ФИО) мастера.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этого действия.")
        await state.clear()
        return

    photo_id = message.photo[-1].file_id  # Получаем file_id самого большого фото
    await state.update_data(newMasterPhotoId=photo_id)
    await message.answer("Введите ФИО мастера:")
    await state.set_state(AdminMasterState.addMasterWaitingForFullName)


@admin_masters_router.message(AdminMasterState.addMasterWaitingForPhoto)
async def handlerAdminAddMasterPhotoInvalid(message: Message):
    """
    Обрабатывает неверный ввод (не фото) при ожидании фотографии.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этого действия.")
        return
    await message.answer("Пожалуйста, отправьте фото мастера.")


# --- Добавление мастера: Шаг 2 (Полное имя) ---
@admin_masters_router.message(AdminMasterState.addMasterWaitingForFullName)
async def handlerAdminAddMasterFullName(message: Message, state: FSMContext):
    """
    Обрабатывает ввод полного имени для нового мастера.
    Запрашивает комментарий/описание для мастера.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этого действия.")
        await state.clear()
        return

    master_full_name = message.text.strip()
    if not master_full_name:
        await message.answer("ФИО мастера не может быть пустым. Пожалуйста, введите ФИО:")
        return
    await state.update_data(newMasterFullName=master_full_name)
    await message.answer("Введите комментарий о мастере (о себе):")
    await state.set_state(AdminMasterState.addMasterWaitingForComment)


# --- Добавление мастера: Шаг 3 (Комментарий/Описание) ---
@admin_masters_router.message(AdminMasterState.addMasterWaitingForComment)
async def handlerAdminAddMasterComment(message: Message, state: FSMContext):
    """
    Обрабатывает ввод комментария/описания для нового мастера.
    Предлагает выбрать услуги, предоставляемые мастером.
    """
    if not await db_requests.isUserAdmin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этого действия.")
        await state.clear()
        return

    master_comment = message.text.strip()
    if not master_comment:
        await message.answer("Комментарий не может быть пустым. Пожалуйста, введите комментарий:")
        return
    await state.update_data(newMasterComment=master_comment)

    # Получаем все услуги, чтобы разрешить выбор
    services = await db_requests.getServices()
    if not services:
        await message.answer("Нет доступных услуг для привязки к мастеру. Пожалуйста, сначала добавьте услуги.")
        # Пропускаем выбор услуг и сразу переходим к подтверждению без услуг
        await state.update_data(newMasterSelectedServiceIds=[])
        await displayAddMasterFinalCard(message, state)  # Отображаем итоговую карточку без услуг
        return

    # Инициализируем список выбранных услуг в состоянии
    await state.update_data(newMasterSelectedServiceIds=[])
    await message.answer(
        """Выберите услуги, которые предоставляет мастер:""",
        reply_markup=adminMasterServicesSelectionKeyboard(services, [])
    )
    await state.set_state(AdminMasterState.addMasterChoosingServices)


# --- Добавление мастера: Шаг 4 (Выбор услуг) ---
@admin_masters_router.callback_query(F.data.startswith("adminToggleMasterService_"))
async def handlerAdminToggleMasterService(callback: CallbackQuery, state: FSMContext):
    """
    Переключает выбор услуги для нового мастера.
    Обновляет инлайн-клавиатуру, чтобы отразить выбор.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    current_state = await state.get_state()
    if current_state != AdminMasterState.addMasterChoosingServices:
        await callback.answer("Неверное действие. Пожалуйста, начните добавление мастера заново.", show_alert=True)
        await state.clear()
        return

    service_id = int(callback.data.split("_")[1])
    user_data = await state.get_data()
    selected_service_ids: List[int] = user_data.get('newMasterSelectedServiceIds', [])

    if service_id in selected_service_ids:
        selected_service_ids.remove(service_id)
    else:
        selected_service_ids.append(service_id)

    await state.update_data(newMasterSelectedServiceIds=selected_service_ids)

    services = await db_requests.getServices()
    await callback.message.edit_reply_markup(
        reply_markup=adminMasterServicesSelectionKeyboard(services, selected_service_ids)
    )
    await callback.answer()


@admin_masters_router.callback_query(F.data == "adminConfirmMasterServices")
async def handlerAdminConfirmMasterServices(callback: CallbackQuery, state: FSMContext):
    """
    Подтверждает выбранные услуги для нового мастера.
    Отображает итоговую карточку для подтверждения.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    current_state = await state.get_state()
    if current_state != AdminMasterState.addMasterChoosingServices:
        await callback.answer("Неверное действие. Пожалуйста, начните добавление мастера заново.", show_alert=True)
        await state.clear()
        return

    await displayAddMasterFinalCard(callback.message, state)  # Используем message из callback
    await callback.answer()


# --- Вспомогательная функция для отображения итоговой карточки мастера ---
async def displayAddMasterFinalCard(message: Message, state: FSMContext):
    """
    Формирует и отображает итоговую карточку для добавления мастера.
    """
    user_data = await state.get_data()
    master_full_name = user_data.get('newMasterFullName')
    master_comment = user_data.get('newMasterComment')
    master_photo_id = user_data.get('newMasterPhotoId')
    selected_service_ids = user_data.get('newMasterSelectedServiceIds', [])

    services = await db_requests.getServices()
    selected_service_names = [s.name for s in services if s.id in selected_service_ids]

    final_card_text = f"""<b>Итоговая карточка мастера:</b>

ФИО: <b>{master_full_name}</b>
О себе: {master_comment}
Предоставляет услуги: {', '.join(selected_service_names) if selected_service_names else 'Не выбрано'}

Подтвердите добавление или отмените."""

    # Отправляем фото, если оно есть, и сохраняем ID сообщения
    sent_message = None
    if master_photo_id:
        sent_message = await message.answer_photo(photo=master_photo_id, caption=final_card_text,
                                                  reply_markup=adminAddMasterConfirmKeyboard())
    else:
        sent_message = await message.answer(final_card_text, reply_markup=adminAddMasterConfirmKeyboard())

    # Сохраняем ID сообщения для последующего удаления/редактирования
    await state.update_data(lastAdminMessageId=sent_message.message_id)
    await state.set_state(AdminMasterState.addMasterConfirm)


# --- Добавление мастера: Подтверждение/Отмена ---
import logging

logger = logging.getLogger(__name__)

@admin_masters_router.callback_query(F.data == "adminConfirmAddMaster")
async def handlerAdminConfirmAddMaster(callback: CallbackQuery, state: FSMContext):
    logger.info("handlerAdminConfirmAddMaster: старт обработки")

    current_state = await state.get_state()
    logger.debug(f"Текущий state: {current_state}")
    if current_state != AdminMasterState.addMasterConfirm:
        await callback.answer("Неверное действие. Пожалуйста, начните добавление мастера заново.", show_alert=True)
        await state.clear()
        logger.warning("Неверный state, сброс состояния")
        return

    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        logger.warning(f"Пользователь {callback.from_user.id} не админ")
        return

    user_data = await state.get_data()
    logger.debug(f"Данные из state: {user_data}")

    master_full_name = user_data.get('newMasterFullName')
    master_comment = user_data.get('newMasterComment')
    master_photo_id = user_data.get('newMasterPhotoId')
    selected_service_ids = user_data.get('newMasterSelectedServiceIds', [])
    last_admin_message_id = user_data.get('lastAdminMessageId')

    try:
        logger.info(f"Попытка добавить мастера: {master_full_name}")
        new_barber = await db_requests.addBarber(
            name=master_full_name,
            description=master_comment,
            photo_id=master_photo_id,
            service_ids=selected_service_ids
        )
        logger.info(f"Мастер добавлен: ID={new_barber.id}, Имя={new_barber.name}")

        if last_admin_message_id:
            try:
                await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=last_admin_message_id)
                logger.debug(f"Предыдущее сообщение {last_admin_message_id} удалено")
            except Exception as delete_e:
                logger.error(f"Ошибка при удалении предыдущего сообщения: {delete_e}")

        await callback.message.answer(f"✅ Мастер <b>{new_barber.name}</b> успешно добавлен!")
    except Exception as e:
        logger.error(f"Ошибка при добавлении мастера: {e}", exc_info=True)
        if last_admin_message_id:
            try:
                await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=last_admin_message_id)
                logger.debug(f"Предыдущее сообщение {last_admin_message_id} удалено после ошибки")
            except Exception as delete_e:
                logger.error(f"Ошибка при удалении сообщения после ошибки добавления: {delete_e}")

        await callback.message.answer("Произошла ошибка при добавлении мастера. Пожалуйста, попробуйте позже.")
    finally:
        await state.clear()
        await callback.message.answer("Выберите действие с мастерами:", reply_markup=adminMastersMenuKeyboard())
        await callback.answer()
        logger.info("handlerAdminConfirmAddMaster: обработка завершена")

@admin_masters_router.callback_query(F.data == "adminCancelAddMaster")
async def handlerAdminCancelAddMaster(callback: CallbackQuery, state: FSMContext):
    """
    Отменяет процесс добавления нового мастера.
    """
    current_state = await state.get_state()
    if current_state != AdminMasterState.addMasterConfirm:
        await callback.answer("Неверное действие. Пожалуйста, начните добавление мастера заново.", show_alert=True)
        await state.clear()
        return

    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    user_data = await state.get_data()
    last_admin_message_id = user_data.get('lastAdminMessageId')  # Получаем ID предыдущего сообщения

    if last_admin_message_id:
        try:
            await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=last_admin_message_id)
        except Exception as delete_e:
            print(f"Ошибка при удалении предыдущего сообщения при отмене: {delete_e}")

    await state.clear()
    await callback.message.answer("❌ Добавление мастера отменено.")  # Отправляем новое сообщение
    await callback.message.answer("Выберите действие с мастерами:", reply_markup=adminMastersMenuKeyboard())
    await callback.answer()


# --- Просмотр мастеров ---
@admin_masters_router.callback_query(
    F.data == "adminViewBarbers")  # Убедитесь, что это правильный callback для вызова списка
async def handlerAdminViewBarbersList(callback: CallbackQuery, state: FSMContext):
    """
    Отображает список всех мастеров с пагинацией для просмотра.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear()

    barbers = await db_requests.getBarbers()

    if not barbers:
        await callback.message.edit_text("Пока нет добавленных мастеров.")
        await callback.message.answer("Выберите действие с мастерами:", reply_markup=adminMastersMenuKeyboard())
        await callback.answer()
        return

    await callback.message.edit_text(
        "Выберите мастера для просмотра деталей:",
        reply_markup=getMasterSelectKeyboard(barbers, "adminViewBarber", 0, BOOKINGS_PER_PAGE)
    )
    await callback.answer()


@admin_masters_router.callback_query(F.data.startswith("adminViewBarberPage_"))
async def handlerAdminViewBarbersPaginate(callback: CallbackQuery):
    """
    Обрабатывает пагинацию списка мастеров для просмотра.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    barbers = await db_requests.getBarbers()

    page = int(callback.data.split('_')[-1])

    await callback.message.edit_text(
        "Выберите мастера для просмотра деталей:",
        reply_markup=getMasterSelectKeyboard(barbers, "adminViewBarber", page, BOOKINGS_PER_PAGE)
    )
    await callback.answer()


# --- Просмотр деталей конкретного мастера ---
# ЭТО НОВЫЙ ХЭНДЛЕР, КОТОРЫЙ ВАМ НУЖЕН
@admin_masters_router.callback_query(F.data.startswith("adminViewBarber_"))
async def handlerAdminViewSpecificBarber(callback: CallbackQuery):
    """
    Отображает подробную информацию о выбранном мастере.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    try:
        # action_prefix_barber_id -> "adminViewBarber_123"
        barber_id = int(callback.data.split('_')[-1])
        barber = await db_requests.getBarberById(barber_id)

        if not barber:
            await callback.answer("Мастер не найден.", show_alert=True)
            return

        # Формируем текст с деталями о мастере
        message_text = (
            f"**Мастер: {barber.name}**\n"
            f"ID: {barber.id}\n"
            f"О мастере: {barber.description if barber.description else 'Нет описания'}\n"
            f"Контакты: {barber.contact_info if barber.contact_info else 'Не указаны'}"
        )

    except ValueError:
        await callback.answer("Неверные данные мастера.", show_alert=True)
    except Exception as e:
        await callback.answer(f"Произошла ошибка: {e}", show_alert=True)

    await callback.answer()


# Хэндлер для кнопки "Назад в меню мастеров"
@admin_masters_router.callback_query(F.data == "adminBackToMastersMenu")
async def handlerAdminBackToMastersMenu(callback: CallbackQuery):
    """
    Обрабатывает возврат из просмотра мастеров в меню управления мастерами.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return
    await callback.message.edit_text(
        "Выберите действие с мастерами:",
        reply_markup=adminMastersMenuKeyboard()
    )
    await callback.answer()


@admin_masters_router.callback_query(F.data.startswith("adminViewMaster_"))
async def handlerAdminViewSingleMaster(callback: CallbackQuery, state: FSMContext):
    """
    Отображает детали выбранного мастера.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    master_id = int(callback.data.split("_")[1])
    barber = await db_requests.getBarberById(master_id)

    if not barber:
        await callback.answer("Мастер не найден.", show_alert=True)
        await handlerAdminViewBarbersList(callback, state)  # Возвращаемся к списку
        return

    service_names = [s.name for s in barber.services] if barber.services else []

    master_info_text = f"""<b>Детали мастера:</b>

ФИО: <b>{barber.name}</b>
О себе: {barber.description}
Предоставляет услуги: {', '.join(service_names) if service_names else 'Не указано'}"""

    # Отправляем новое сообщение с фото/текстом и клавиатурой
    if barber.photo_id:
        await callback.message.answer_photo(photo=barber.photo_id, caption=master_info_text,
                                            reply_markup=adminSingleMasterViewKeyboard(barber.id))
    else:
        await callback.message.answer(master_info_text, reply_markup=adminSingleMasterViewKeyboard(barber.id))

    # Удаляем предыдущее сообщение (список мастеров)
    try:
        await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    except Exception as e:
        print(f"Ошибка при удалении предыдущего сообщения списка мастеров: {e}")

    await callback.answer()

# Удаление мастера
@admin_masters_router.callback_query(F.data == "adminDeleteMaster")
async def handlerAdminDeleteMasterStart(callback: CallbackQuery, state: FSMContext):
    """
    Начинает процесс удаления мастера.
    Отображает постраничный список мастеров для выбора.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    # Очищаем любое предыдущее состояние и загружаем мастеров только один раз
    await state.clear()
    barbers = await db_requests.getBarbers()

    if not barbers:
        await callback.message.edit_text("Пока нет мастеров для удаления.")
        await callback.message.answer("Выберите действие с мастерами:", reply_markup=adminMastersMenuKeyboard())
        await callback.answer()
        return

    # Сохраняем список мастеров и текущую страницу в FSMContext
    await state.update_data(barbers=barbers)

    # Исправленный вызов функции
    keyboard = getMasterSelectKeyboard(barbers, "adminSelectDeleteMaster", 0)

    await callback.message.edit_text(
        "Выберите мастера для удаления:",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_masters_router.callback_query(F.data.startswith("adminSelectDeleteMasterPage_"))
async def handlerAdminDeleteMastersPaginate(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает пагинацию списка мастеров в режиме удаления.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    page = int(callback.data.split("_")[1])

    user_data = await state.get_data()
    barbers = user_data.get('barbers')

    if not barbers:
        await callback.message.edit_text("Ошибка. Список мастеров не найден.")
        await state.clear()
        await callback.answer()
        return

    await callback.message.edit_reply_markup(
        reply_markup=getMasterSelectKeyboard(barbers, "adminSelectDeleteMaster", page)
    )
    await callback.answer()


@admin_masters_router.callback_query(F.data.startswith("adminSelectDeleteMaster_"))
async def handlerAdminConfirmDeleteMaster(callback: CallbackQuery, state: FSMContext):
    """
    Запрашивает подтверждение удаления выбранного мастера.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    master_id = int(callback.data.split("_")[1])
    barber = await db_requests.getBarberById(master_id)

    if not barber:
        await callback.answer("Мастер не найден.", show_alert=True)
        await handlerAdminDeleteMasterStart(callback, state)  # Возвращаемся к списку
        return

    await state.update_data(masterToDeleteId=master_id)  # Сохраняем ID для подтверждения
    await callback.message.edit_text(
        f"""Вы действительно хотите удалить мастера: <b>{barber.name}</b>?""",
        reply_markup=adminConfirmDeleteMasterKeyboard(master_id)
    )
    await state.set_state(AdminMasterState.deleteMasterConfirm)  # Устанавливаем состояние для подтверждения
    await callback.answer()


# --- Удаление мастера: Подтверждение ---
@admin_masters_router.callback_query(F.data.startswith("adminExecuteDeleteMaster_"))
async def handlerAdminExecuteDeleteMaster(callback: CallbackQuery, state: FSMContext):
    """
    Выполняет удаление мастера из базы данных после подтверждения.
    """
    current_state = await state.get_state()
    user_data = await state.get_data()
    master_id = int(callback.data.split("_")[1])

    if current_state != AdminMasterState.deleteMasterConfirm:
        await callback.answer("Неверное действие. Пожалуйста, начните удаление мастера заново.", show_alert=True)
        await state.clear()
        return

    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    try:
        success = await db_requests.deleteBarber(master_id)
        if success:
            await callback.message.edit_text("🗑️ Мастер успешно удален.")
        else:
            await callback.message.edit_text("Произошла ошибка при удалении мастера. Возможно, мастер уже удален.")
    except Exception as e:
        print(f"Ошибка при удалении мастера: {e}")
        await callback.message.answer("Произошла ошибка при удалении мастера. Пожалуйста, попробуйте позже.")
    finally:
        await state.clear()
        await callback.message.answer("Выберите действие с мастерами:", reply_markup=adminMastersMenuKeyboard())
        await callback.answer()


@admin_masters_router.callback_query(F.data == "cancelDeleteMaster")
async def handlerAdminCancelDeleteMaster(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает отмену удаления мастера и возвращает в главное меню.
    """
    await state.clear()
    await callback.message.edit_text("Действие отменено.")
    await callback.message.answer("Выберите действие с мастерами:", reply_markup=adminMastersMenuKeyboard())
    await callback.answer()

# --- Управление отпуском: Шаг 1 (Выбор мастера) ---
@admin_masters_router.callback_query(F.data == "adminMasterVacation")
async def handlerAdminMasterVacationStart(callback: CallbackQuery, state: FSMContext):
    """
    Начинает процесс установки отпуска для мастера.
    Отображает список мастеров для выбора с пагинацией.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    # Очищаем состояние и загружаем мастеров только один раз
    await state.clear()
    async with db_requests._async_session_factory() as session:
        barbers = await db_requests.getBarbers()

    if not barbers:
        await callback.message.edit_text("Пока нет мастеров для настройки отпуска.")
        await callback.message.answer("Выберите действие с мастерами:", reply_markup=adminMastersMenuKeyboard())
        await callback.answer()
        return

    # Сохраняем список мастеров и текущую страницу в FSMContext
    await state.update_data(barbers=barbers, page=0)
    await state.set_state(AdminMasterState.vacationChooseMaster)

    keyboard = getMasterSelectKeyboard(page=0, barbers=barbers)
    await callback.message.edit_text(
        "Выберите мастера, которого хотите отправить в отпуск:",
        reply_markup=keyboard
    )
    await callback.answer()

MASTERS_PER_PAGE = 5


@admin_masters_router.callback_query(F.data.startswith("master_vacation_page_"))
async def handlerAdminMasterVacationPaginate(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатия на кнопки пагинации (стрелки).
    """
    data = await state.get_data()
    barbers = data.get('barbers')
    current_page = data.get('page', 0)

    if not barbers:
        await callback.message.edit_text("Ошибка. Список мастеров не найден.")
        await state.clear()
        await callback.answer()
        return

    action, page_str = callback.data.split(':')

    new_page = current_page
    if "next" in action:
        new_page = current_page + 1
    elif "prev" in action:
        new_page = current_page - 1

    total_pages = (len(barbers) + MASTERS_PER_PAGE - 1) // MASTERS_PER_PAGE

    if 0 <= new_page < total_pages:
        await state.update_data(page=new_page)
        keyboard = getMasterSelectKeyboard(page=new_page, barbers=barbers)
        await callback.message.edit_reply_markup(reply_markup=keyboard)

    await callback.answer()


# Хэндлер для кнопки "Назад"
@admin_masters_router.callback_query(F.data == "adminMastersBack")
async def handlerAdminMastersBack(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатие на кнопку "Назад", возвращая в главное меню админа.
    """
    await state.clear()
    await callback.message.edit_text("Выберите действие с мастерами:", reply_markup=adminMastersMenuKeyboard())
    await callback.answer()


@admin_masters_router.callback_query(F.data.startswith("adminSelectVacationMaster_"))
async def handlerAdminMasterVacationChooseMaster(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор мастера для отпуска.
    Предлагает выбрать дату начала отпуска.
    """
    current_state = await state.get_state()
    if current_state != AdminMasterState.vacationChooseMaster:
        await callback.answer("Неверное действие. Пожалуйста, начните настройку отпуска заново.", show_alert=True)
        await state.clear()
        return

    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    master_id = int(callback.data.split("_")[1])
    barber = await db_requests.getBarberById(master_id)

    if not barber:
        await callback.answer("Мастер не найден.", show_alert=True)
        await handlerAdminMasterVacationStart(callback, state)  # Возвращаемся к списку
        return

    await state.update_data(vacationMasterId=master_id, vacationMasterName=barber.name)
    await callback.message.edit_text(
        f"""Вы выбрали мастера: <b>{barber.name}</b>.
Выберите дату начала отпуска:""",
        reply_markup=adminMasterVacationCalendarKeyboard()
    )
    await state.set_state(AdminMasterState.vacationChooseStartDate)
    await callback.answer()


# --- Управление отпуском: Шаг 2 (Выбор даты начала) ---
@admin_masters_router.callback_query(F.data.startswith("adminVacationNavigateMonth_") | F.data.startswith(
    "adminVacationNavigateYear_") | F.data.startswith("adminVacationDate_"))
async def handlerAdminMasterVacationCalendarNavigationOrSelection(callback: CallbackQuery, state: FSMContext):
    """
    Единый хэндлер для навигации по календарю и выбора даты для начала/окончания отпуска.
    """
    current_state = await state.get_state()
    if current_state not in [AdminMasterState.vacationChooseStartDate, AdminMasterState.vacationChooseEndDate]:
        await callback.answer("Неверное действие. Пожалуйста, начните настройку отпуска заново.", show_alert=True)
        await state.clear()
        return

    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    user_data = await state.get_data()
    current_calendar_display_date: date = user_data.get('calendar_display_date', date.today())
    vacation_start_date: Optional[date] = user_data.get('vacationStartDate')  # Дата начала, если уже выбрана

    action_data = callback.data.split("_")
    action_type = action_data[0]
    value = action_data[1]

    new_calendar_display_date = current_calendar_display_date  # По умолчанию текущая отображаемая дата

    if action_type == "adminVacationNavigateMonth":
        new_calendar_display_date = datetime.strptime(value, "%Y-%m").date()
    elif action_type == "adminVacationNavigateYear":
        new_year = int(value)
        new_calendar_display_date = current_calendar_display_date.replace(year=new_year)
    elif action_type == "adminVacationDate":
        chosen_date = datetime.strptime(value, "%Y-%m-%d").date()

        if current_state == AdminMasterState.vacationChooseStartDate:
            if chosen_date < date.today():
                await callback.answer("Нельзя выбрать прошедшую дату для начала отпуска.", show_alert=True)
                return
            await state.update_data(vacationStartDate=chosen_date)
            await state.update_data(calendar_display_date=chosen_date)  # Сбрасываем календарь на выбранный месяц

            await callback.message.edit_text(
                f"""Начало отпуска: <b>{chosen_date.strftime('%d.%m.%Y')}</b>.
Выберите дату окончания отпуска:""",
                reply_markup=adminMasterVacationCalendarKeyboard(chosen_date, chosen_date)
                # Передаем дату начала для ограничения
            )
            await state.set_state(AdminMasterState.vacationChooseEndDate)
            await callback.answer()
            return  # Выходим, так как состояние изменилось

        elif current_state == AdminMasterState.vacationChooseEndDate:
            if not vacation_start_date or chosen_date < vacation_start_date:
                await callback.answer("Дата окончания отпуска не может быть раньше даты начала.", show_alert=True)
                return
            await state.update_data(vacationEndDate=chosen_date)
            await displayAdminMasterVacationFinalCard(callback.message, state)
            await callback.answer()
            return  # Выходим, так как состояние изменилось

    await state.update_data(calendar_display_date=new_calendar_display_date)

    # Обновляем клавиатуру календаря с учетом новой отображаемой даты и minDate
    await callback.message.edit_reply_markup(
        reply_markup=adminMasterVacationCalendarKeyboard(new_calendar_display_date,
                                                         vacation_start_date if current_state == AdminMasterState.vacationChooseEndDate else date.today())
    )
    await callback.answer()


# --- Вспомогательная функция для отображения итоговой карточки отпуска мастера ---
async def displayAdminMasterVacationFinalCard(message: Message, state: FSMContext):
    """
    Формирует и отображает итоговую карточку для отпуска мастера.
    """
    user_data = await state.get_data()
    master_name: str = user_data.get('vacationMasterName')
    start_date: date = user_data.get('vacationStartDate')
    end_date: date = user_data.get('vacationEndDate')

    final_card_text = f"""<b>Отпуск мастера:</b>

Мастер: <b>{master_name}</b>
Начало отпуска: <b>{start_date.strftime('%d.%m.%Y')}</b>
Конец отпуска: <b>{end_date.strftime('%d.%m.%Y')}</b>

Подтвердите или отмените."""
    await message.edit_text(final_card_text, reply_markup=adminMasterVacationConfirmKeyboard())
    await state.set_state(AdminMasterState.vacationConfirm)


# --- Управление отпуском: Подтверждение/Отмена ---
@admin_masters_router.callback_query(F.data == "adminConfirmVacation")
async def handlerAdminConfirmVacation(callback: CallbackQuery, state: FSMContext):
    """
    Подтверждает и сохраняет период отпуска для мастера в базе данных.
    """
    current_state = await state.get_state()
    if current_state != AdminMasterState.vacationConfirm:
        await callback.answer("Неверное действие. Пожалуйста, начните настройку отпуска заново.", show_alert=True)
        await state.clear()
        return

    # Проверка на права администратора
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    user_data = await state.get_data()
    master_id = user_data.get('vacationMasterId')
    start_date = user_data.get('vacationStartDate')
    end_date = user_data.get('vacationEndDate')
    master_name = user_data.get('vacationMasterName')

    if not all([master_id, start_date, end_date]):
        await callback.message.edit_text("Произошла ошибка. Не удалось получить данные об отпуске. Пожалуйста, начните настройку заново.")
        await state.clear()
        await callback.answer("Ошибка: неполные данные.", show_alert=True)
        return

    try:
        # Используем глобальную фабрику сессий
        if db_requests._async_session_factory is None:
            raise RuntimeError("Фабрика сессий базы данных не инициализирована.")
        async with db_requests._async_session_factory() as session:
            await db_requests.addMasterVacation(session, master_id, start_date, end_date)

        await callback.message.edit_text(f"✅ Отпуск для мастера <b>{master_name}</b> успешно добавлен!")

    except Exception as e:
        print(f"Ошибка при добавлении отпуска мастера: {e}")
        await callback.message.edit_text("Произошла ошибка при добавлении отпуска. Пожалуйста, попробуйте позже.")
    finally:
        await state.clear()
        await callback.message.answer("Выберите действие с мастерами:", reply_markup=adminMastersMenuKeyboard())
        await callback.answer()



@admin_masters_router.callback_query(F.data == "adminCancelVacation")
async def handlerAdminCancelVacation(callback: CallbackQuery, state: FSMContext):
    """
    Отменяет процесс установки отпуска для мастера.
    """
    current_state = await state.get_state()
    if current_state != AdminMasterState.vacationConfirm:
        await callback.answer("Неверное действие. Пожалуйста, начните настройку отпуска заново.", show_alert=True)
        await state.clear()
        return

    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text("❌ Настройка отпуска отменена.")
    await callback.message.answer("Выберите действие с мастерами:", reply_markup=adminMastersMenuKeyboard())
    await callback.answer()


# --- Общие хэндлеры отмены для админ-панели (если нужны из этого роутера) ---
@admin_masters_router.callback_query(F.data == "adminCancelOperation")
async def handlerAdminCancelOperation(callback: CallbackQuery, state: FSMContext):
    """
    Общий хэндлер для отмены любой текущей административной операции и возврата в меню мастеров.
    """
    if not await db_requests.isUserAdmin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этого действия.", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text("Операция отменена.")
    await callback.message.answer("Выберите действие с мастерами:", reply_markup=adminMastersMenuKeyboard())
    await callback.answer()
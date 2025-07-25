from aiogram import Router

from app.handlers.user import handler_start, handler_appointment, handler_registration, handler_info, handler_support, handlers_my_bookings

main_router = Router()

main_router.include_router(handler_start.start_router)
main_router.include_router(handler_registration.registration_router)
main_router.include_router(handler_appointment.appointment_router)
main_router.include_router(handler_support.support_router)
main_router.include_router(handler_info.about_us_router)
main_router.include_router(handlers_my_bookings.my_bookings_router)


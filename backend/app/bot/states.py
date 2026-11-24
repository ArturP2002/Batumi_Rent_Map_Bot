from aiogram.fsm.state import State, StatesGroup


class AddPropertyFSM(StatesGroup):
    rent_type = State()
    rooms = State()
    area = State()
    floor = State()
    price = State()
    district = State()
    address = State()
    location = State()
    amenities = State()
    sleeping = State()
    description = State()
    photos = State()
    preview = State()


class DealFSM(StatesGroup):
    choose_inquiry = State()
    dates = State()


class CalendarFSM(StatesGroup):
    choose_property = State()
    start = State()
    end = State()


class RealtorAuthFSM(StatesGroup):
    choose_action = State()
    register_email = State()
    register_password = State()
    register_password_confirm = State()
    register_name = State()
    login_email = State()
    login_password = State()

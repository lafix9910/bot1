from aiogram.fsm.state import State, StatesGroup


class BookingState(StatesGroup):
    service = State()
    master = State()
    date = State()
    time = State()
    confirm = State()


class RescheduleState(StatesGroup):
    booking_id = State()
    new_date = State()
    new_time = State()
    confirm = State()


class AdminAddMasterState(StatesGroup):
    name = State()
    username = State()
    bio = State()


class AdminWorkingHoursState(StatesGroup):
    start_hour = State()
    end_hour = State()


class AdminAddServiceState(StatesGroup):
    name = State()
    price = State()
    description = State()
    duration = State()

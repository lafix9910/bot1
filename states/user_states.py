from aiogram.fsm.state import State, StatesGroup


class BookingState(StatesGroup):
    service = State()
    master = State()
    date = State()
    time = State()
    name = State()
    phone = State()
    comment = State()
    confirm = State()


class RescheduleState(StatesGroup):
    """FSM для клиента - изменение времени записи"""
    booking_id = State()
    master_id = State()
    new_date = State()
    new_time = State()


class AdminRescheduleState(StatesGroup):
    """FSM для админа - изменение времени записи"""
    booking_id = State()
    master_id = State()
    new_date = State()
    new_time = State()


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

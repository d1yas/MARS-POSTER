from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

class PostState(StatesGroup):
    photo = State()
    caption = State()

class ElonState(StatesGroup):
    photo = State()
    caption = State()
    time = State()  # Vaqt uchun holat

class UpdateTimeState(StatesGroup):
    # waiting_for_time = State()
    waiting_for_new_time = State()
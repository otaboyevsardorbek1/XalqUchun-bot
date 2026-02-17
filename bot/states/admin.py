from aiogram.fsm.state import State, StatesGroup

class CourierState(StatesGroup):
    waiting_for_courier_phone = State()
    waiting_for_cancel_reason = State()

class AdminStates(StatesGroup):
    waiting_for_courier_phone = State()
    waiting_for_cancel_reason = State()

class BroadcastState(StatesGroup):
    waiting_for_broadcast_text = State()
    waiting_for_broadcast_photo = State()
    waiting_for_broadcast_video = State()
    waiting_for_broadcast_document = State()
    waiting_for_broadcast_text_and_photo = State()
    waiting_for_broadcast_text_and_video = State()
    waiting_for_broadcast_text_and_document = State()
    # Qo‘shimcha ikkinchi bosqichlar
    waiting_for_broadcast_text_and_photo_step2 = State()
    waiting_for_broadcast_text_and_video_step2 = State()
    waiting_for_broadcast_text_and_document_step2 = State()
    waiting_for_broadcast_text_and_media_type = State()  # tasdiqlash uchun
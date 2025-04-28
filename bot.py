import asyncio
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from database import connect, cursor, add_post, mark_post_as_sent, get_post_times, updateting_post_time
from aiogram.types import ReplyKeyboardMarkup,  KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton,ChatMemberStatus,  ChatType
from dotenv import load_dotenv
import os



load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMINS = os.getenv("ADMINS").split(",")  # ['6812498519', '2122893555']


# TOKEN = "7581959377:AAEhAfvaMyNKQtB5eGnkGWSeFiAryXb5IZU"
# ADMINS = ["6812498519"]

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class PostState(StatesGroup):
    choice = State()  # Forward yoki Qolda tanlovi
    forward = State()  # Forward tanlansa
    photo = State()    # Qolda rasm yuklash
    caption = State()
    shablon = State()


class ElonState(StatesGroup):
    photo = State()
    caption = State()
    time = State()

class UpdateTimeState(StatesGroup):
    waiting_for_new_time = State()

# Buttonlar
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

btn_start = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📮Post jo`natish"), KeyboardButton(text="🧾Elon qo`shish")],
        [KeyboardButton(text="📑 Postlar ➡️"), KeyboardButton(text="👥 Guruhlar 🗣")]
    ],
    resize_keyboard=True
)

posts_btn = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Forward qilish"), KeyboardButton(text="✍️ Qo'lda kiritish")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ],
    resize_keyboard=True
)

btn_cancel = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
    resize_keyboard=True
)

FORBIDDEN_TEXTS = [
    "📮Post jo`natish", "🧾Elon qo`shish", "❌ Bekor qilish",
    "/start", "/posts", "/groups", "🔄 Forward qilish", "✍️ Qo'lda kiritish"
]

# Admin ekanligini tekshirish
def is_admin(user_id):
    return str(user_id) in ADMINS

async def admin_filter(message: types.Message):
    return is_admin(message.from_user.id)

@dp.message_handler(lambda message: message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and 
                    message.text and (any(text in message.text for text in FORBIDDEN_TEXTS) or message.text.startswith("/start@")))
async def delete_if_not_admin(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except Exception as e:
        print(f"👤 Admin tekshirib bo‘lmadi: {e}")
        return

    if member.status not in ['administrator', 'creator']:
        try:
            await message.delete()
            print(f"🗑 O‘chirildi: {message.text} (from {user_id}) in chat {chat_id}")
        except Exception as e:
            print(f"❗ O‘chirishda xatolik: {e}")




# Barcha xabarlar uchun middleware
@dp.message_handler(lambda message: not is_admin(message.from_user.id), state="*")
async def ignore_non_admin(message: types.Message):
    # Oddiy foydalanuvchilar uchun hech qanday javob yo'q
    return


@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    if is_admin(message.from_user.id):
        await message.answer(
            f"👋 Salom, {message.from_user.full_name}!\n"
            f"🤖 Bot faqat adminlar uchun ishlaydi.",
            reply_markup=btn_start
        )
    else:
        return
    
@dp.message_handler(text="📑 Postlar ➡️")
async def show_posts(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    posts = cursor.execute("SELECT id, photo, caption, post_time FROM active_posts WHERE status != 'deleted'").fetchall()
    
    if not posts:
        await message.answer("📭 Hozirda aktiv postlar yo'q.")
        return
        
    await message.answer(f"📋 Jami {len(posts)} ta aktiv post mavjud:")
    
    for post in posts:
        post_id, photo, caption, post_time = post
        
        inline_kb = InlineKeyboardMarkup(row_width=2)
        delete_btn = InlineKeyboardButton("🗑 O'chirish", callback_data=f"delete:{post_id}")
        update_time_btn = InlineKeyboardButton("🕒 Vaqtni yangilash", callback_data=f"update_time:{post_id}")
        new_time = InlineKeyboardButton("Yangi vaqt qoshish", callback_data=f"new_time:{post_id}")
        inline_kb.add(delete_btn, update_time_btn, new_time)
        
        # Determine content type based on photo field
        if photo == "TEXT_ONLY":
            # For text-only posts
            await message.answer(
                f"📝 Post #{post_id} (Matn)\n"
                f"⏰ Vaqt: {post_time}\n\n"
                f"{caption}",
                reply_markup=inline_kb
            )
        elif photo.startswith("VIDEO:"):
            # For video posts
            video_id = photo[6:]  # Remove "VIDEO:" prefix
            try:
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=video_id,
                    caption=f"📝 Post #{post_id} (Video)\n"
                            f"⏰ Vaqt: {post_time}\n\n"
                            f"{caption}",
                    reply_markup=inline_kb
                )
            except Exception as e:
                await message.answer(
                    f"📝 Post #{post_id} (Video - ko'rsatib bo'lmadi)\n"
                    f"⏰ Vaqt: {post_time}\n\n"
                    f"{caption}",
                    reply_markup=inline_kb
                )
        else:
            # For photo posts
            try:
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=photo,
                    caption=f"📝 Post #{post_id}\n"
                            f"⏰ Vaqt: {post_time}\n\n"
                            f"{caption}",
                    reply_markup=inline_kb
                )
            except Exception as e:
                await message.answer(
                    f"📝 Post #{post_id} (Rasm - ko'rsatib bo'lmadi)\n"
                    f"⏰ Vaqt: {post_time}\n\n"
                    f"{caption}",
                    reply_markup=inline_kb
                )

@dp.message_handler(text="👥 Guruhlar 🗣")
async def show_groups(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    groups = cursor.execute("SELECT group_id, group_name, joined_date FROM active_groups").fetchall()
    
    if not groups:
        await message.answer("📭 Hozirda aktiv guruhlar yo'q.")
        return
        
    await message.answer(f"📋 Jami {len(groups)} ta aktiv guruh mavjud:")
    
    for group in groups:
        group_id, group_name, joined_date = group
        await message.answer(
            f"👥 {group_name}\n"
            f"🆔 {group_id}\n"
            f"📅 Qo'shilgan sana: {joined_date}"
        )

@dp.message_handler(content_types=types.ContentType.LEFT_CHAT_MEMBER)
async def bot_removed_from_group(message: types.Message):
    bot_info = await bot.get_me()
    left_member = message.left_chat_member
    
    if left_member.id == bot_info.id:
        group_id = str(message.chat.id)
        group_name = message.chat.title
        
        # Guruhni bazadan o'chirish
        cursor.execute("DELETE FROM active_groups WHERE group_id = ?", (group_id,))
        connect.commit()
        
        # Adminga xabar berish
        for admin_id in ADMINS:
            try:
                await bot.send_message(
                    admin_id, 
                    f"❌ Bot guruhdan chiqarildi: {group_name} ({group_id})\n"
                    f"✅ Guruh ma'lumotlari bazadan o'chirildi."
                )
            except Exception as e:
                print(f"Admin {admin_id}ga xabar yuborib bo'lmadi: {e}")

@dp.callback_query_handler(lambda c: not is_admin(c.from_user.id), state="*")
async def ignore_non_admin_callback(callback_query: types.CallbackQuery):
    return

@dp.callback_query_handler(lambda c: c.data.startswith('new_time:'))
async def process_new_time(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        return
        
    post_id = int(callback_query.data.split(':')[1])
    
    await state.update_data(post_id=post_id)
    
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        f"⏰ Post #{post_id} uchun yangi vaqtni kiriting (HH:MM formatida, masalan: 00:01):"
    )
    
    await UpdateTimeState.waiting_for_new_time.set()

@dp.message_handler(state=UpdateTimeState.waiting_for_new_time)
async def add_new_post_time(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    time_text = message.text
    if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time_text):
        await message.answer("⚠️ Noto'g'ri vaqt formati. Iltimos, vaqtni HH:MM formatida kiriting (masalan: 00:01):")
        return
    
    data = await state.get_data()
    post_id = data.get("post_id")
    post_times = get_post_times(post_id)
    post_times.append(time_text)

    updated_times = ",".join(post_times)
    updateting_post_time(post_id, updated_times)
    
    await message.answer(f"✅ Post #{post_id} vaqtlari {', '.join(post_times)} ga yangilandi!")
    
    await state.finish()

# Modify this handler to properly handle manual photo uploads
@dp.message_handler(content_types=types.ContentType.PHOTO, state=PostState.photo)
async def get_post_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    # Save the photo ID from the upload
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    
    # Ask for caption
    await message.answer("✍️ Endi post uchun izoh (caption) yuboring:", reply_markup=btn_cancel)
    await PostState.caption.set()



    
    
@dp.callback_query_handler(lambda c: c.data.startswith('delete:'))
async def process_delete_post(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        return
    
    post_id = int(callback_query.data.split(':')[1])
    
    cursor.execute("UPDATE active_posts SET status = 'deleted' WHERE id = ?", (post_id,))
    connect.commit()
    
    await bot.answer_callback_query(callback_query.id, text=f"Post #{post_id} o'chirildi!")
    
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption=f"🗑 POST #{post_id} O'CHIRILDI!",
        reply_markup=None
    )

@dp.callback_query_handler(lambda c: c.data.startswith('update_time:'))
async def process_update_time(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        return
        
    post_id = int(callback_query.data.split(':')[1])
    
    await state.update_data(post_id=post_id)
    
    data = await state.get_data()
    post_id = data.get("post_id")
    post_times = get_post_times(post_id)
    update_times_btn = InlineKeyboardMarkup(row_width=3)  # 3 ta tugma bir qatorda
    
    # Har bir vaqt uchun tugma qo'shamiz
    for time in post_times:
        button = InlineKeyboardButton(text=time, callback_data=f"time_{post_id}_{time}")
        update_times_btn.add(button)
    update_times_btn.add(InlineKeyboardButton("Bosh menyu", callback_data="main_menu"))
    
    await callback_query.message.answer(f"⏰ Post #{post_id} uchun qaysi vaqtni o'zgartirmoqchisz ?", reply_markup=update_times_btn)

@dp.callback_query_handler(lambda c: c.data.startswith('time_'))
async def process_update_time(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        return
        
    time = callback_query.data.split('_')[-1]
    post_id = callback_query.data.split('_')[1]
   
    post_times = get_post_times(post_id)
    
    post_times.remove(time)
    
    updated_times = ",".join(post_times)
    updateting_post_time(post_id, updated_times)
    new_times_btn = InlineKeyboardMarkup(row_width=1)  # 3 ta tugma bir qatorda
    # Har bir vaqt uchun tugma qo'shamiz
    await bot.answer_callback_query(callback_query.id, text=f"Post #{post_id} uchun vaqt {time} o'chirildi!")
    
    for a in post_times:
        button = InlineKeyboardButton(text=a, callback_data=f"time_{post_id}_{a}")
        new_times_btn.add(button)
    new_times_btn.add(InlineKeyboardButton("Bosh menyu", callback_data="main_menu"))
    
    await callback_query.message.edit_reply_markup(reply_markup=new_times_btn)

@dp.callback_query_handler(lambda c: c.data == "main_menu")
async def main_menu(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        return
        
    await callback_query.message.delete()
    await bot.send_message(callback_query.from_user.id, "Bosh menyu", reply_markup=btn_start)

# 📮 Post jo'natish tugmasi bosilganda
@dp.message_handler(lambda message: message.text == "📮Post jo`natish")
async def ask_for_post_type(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer("Postni qanday yubormoqchisiz?", reply_markup=posts_btn)
    await PostState.choice.set()

@dp.message_handler(lambda message: message.text in ["🔄 Forward qilish", "✍️ Qo'lda kiritish"], state=PostState.choice)
async def handle_post_choice(message: types.Message, state: FSMContext):
    if message.text == "🔄 Forward qilish":
        await message.answer("📨 Kanaldan xabarni forward qiling:")
        await PostState.forward.set()
    elif message.text == "✍️ Qo'lda kiritish":
        await message.answer("📤 Iltimos, post uchun rasm yuboring:", reply_markup=btn_cancel)
        await PostState.photo.set()

@dp.message_handler(lambda m: m.media_group_id is not None, state=PostState.forward,
                    content_types=types.ContentTypes.ANY)
async def handle_forwarded_media_group(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    if not message.forward_from_chat:
        await message.answer("❌ Bu forward qilingan xabar emas. Iltimos, kanaldan xabarni forward qiling:", reply_markup=btn_cancel)
        return
    
    # Store media group messages and process them after a delay
    post_media_groups[message.media_group_id].append(message)
    if message.media_group_id in post_tasks:
        post_tasks[message.media_group_id].cancel()
    
    post_tasks[message.media_group_id] = asyncio.create_task(
        process_forwarded_media_group(message.media_group_id, message, state)
    )

async def process_forwarded_media_group(media_group_id, sample_msg, state):
    try:
        # Wait to collect all media group messages
        await asyncio.sleep(1.5)
        messages = post_media_groups.pop(media_group_id, [])
        post_tasks.pop(media_group_id, None)
        
        if not messages:
            return
            
        # Get the caption from the first message
        caption = messages[0].caption or ""
        
        # Create media group
        media = []
        for msg in messages:
            if msg.photo:
                media.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=caption if not media else None))
            elif msg.video:
                media.append(InputMediaVideo(media=msg.video.file_id, caption=caption if not media else None))
        
        # Get all groups from database
        groups = cursor.execute("SELECT group_id, group_name, joined_date FROM active_groups").fetchall()
        
        if not groups:
            await sample_msg.answer("❌ Hech qanday aktiv guruh topilmadi.", reply_markup=btn_start)
            await state.finish()
            return
        
        sent_count = 0
        for group in groups:
            group_id = group[0]
            try:
                # Send the media group to each chat
                await bot.send_media_group(chat_id=group_id, media=media)
                sent_count += 1
            except Exception as e:
                print(f"⚠️ {group[1]} ({group_id}) ga media group jo'natib bo'lmadi: {e}")
        
        await sample_msg.answer(f"📢 {sent_count} ta guruhga forward qilingan media group jo'natildi!", reply_markup=btn_start)
        await state.finish()
    except asyncio.CancelledError:
        pass

@dp.message_handler(state=PostState.forward, content_types=types.ContentTypes.ANY)
async def handle_forwarded_message(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    # Skip if it's part of a media group (handled by another handler)
    if message.media_group_id is not None:
        return
        
    if not message.forward_from_chat:
        await message.answer("❌ Bu forward qilingan xabar emas. Iltimos, kanaldan xabarni forward qiling:", reply_markup=btn_cancel)
        return
    
    # Get all groups from database
    groups = cursor.execute("SELECT group_id, group_name, joined_date FROM active_groups").fetchall()
    
    if not groups:
        await message.answer("❌ Hech qanday aktiv guruh topilmadi.", reply_markup=btn_start)
        await state.finish()
        return
    
    sent_count = 0
    for group in groups:
        group_id, group_name, joined_date = group
        try:
            # Forward the same content type
            if message.photo:
                await bot.send_photo(
                    chat_id=group_id, 
                    photo=message.photo[-1].file_id, 
                    caption=message.caption
                )
            elif message.video:
                await bot.send_video(
                    chat_id=group_id, 
                    video=message.video.file_id, 
                    caption=message.caption
                )
            elif message.text:
                await bot.send_message(
                    chat_id=group_id, 
                    text=message.text
                )
            elif message.animation:
                await bot.send_animation(
                    chat_id=group_id, 
                    animation=message.animation.file_id, 
                    caption=message.caption
                )
            elif message.audio:
                await bot.send_audio(
                    chat_id=group_id, 
                    audio=message.audio.file_id, 
                    caption=message.caption
                )
            elif message.document:
                await bot.send_document(
                    chat_id=group_id, 
                    document=message.document.file_id, 
                    caption=message.caption
                )
            elif message.voice:
                await bot.send_voice(
                    chat_id=group_id, 
                    voice=message.voice.file_id, 
                    caption=message.caption
                )
            sent_count += 1
        except Exception as e:
            print(f"⚠️ {group_name} ({group_id}) ga jo'natib bo'lmadi: {e}")
    
    await message.answer(f"📢 {sent_count} ta guruhga forward qilingan post jo'natildi!", reply_markup=btn_start)
    await state.finish()



# 🧾 Elon qo'shish tugmasi bosilganda
@dp.message_handler(lambda message: message.text == "🧾Elon qo`shish")
async def ask_for_elon_photo(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    await message.answer("📤 Iltimos, e'lon uchun rasm yuboring:", reply_markup=btn_cancel)
    await ElonState.photo.set()

# ❌ Bekor qilish tugmasi bosilganda
@dp.message_handler(lambda message: message.text == "❌ Bekor qilish", state="*")
async def cancel_post(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    await state.finish()
    await message.answer("🚫 Amal bekor qilindi.", reply_markup=btn_start)

# Post uchun captionni qabul qilish va jo'natish
@dp.message_handler(state=PostState.caption)
async def get_post_caption(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    caption = message.text
    data = await state.get_data()
    photo_id = data.get("photo")

    # Bazadan barcha guruhlarni olish
    groups = cursor.execute("SELECT group_id, group_name, joined_date FROM active_groups").fetchall()

    if groups:
        sent_count = 0
        for group in groups:
            group_id, group_name, joined_date = group
            try:
                await bot.send_photo(chat_id=group_id, photo=photo_id, caption=caption)
                sent_count += 1
            except Exception as e:
                print(f"⚠️ {group_name} ({group_id}) ga jo'natib bo'lmadi: {e}")

        await message.answer(f"📢 {sent_count} ta guruhga rasm bilan post jo'natildi!", reply_markup=btn_start)
    else:
        await message.answer("❌ Hech qanday aktiv guruh topilmadi.", reply_markup=btn_start)

    await state.finish()

# E'lon uchun rasmni qabul qilish
# E'lon uchun rasmni qabul qilish
@dp.message_handler(content_types=types.ContentType.PHOTO, state=ElonState.photo)
async def get_elon_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    # Check if the message is forwarded
    if message.forward_from_chat:
        # Reject forwarded messages
        await message.answer("⚠️ E'lon uchun forward qilingan xabarlar qabul qilinmaydi. Iltimos, yangi rasm yuboring:", reply_markup=btn_cancel)
        return
    else:
        # Regular photo upload flow
        photo_id = message.photo[-1].file_id
        await state.update_data(photo=photo_id)
        await message.answer("✍️ Endi e'lon uchun izoh (caption) yuboring:", reply_markup=btn_cancel)
        await ElonState.caption.set()

# E'lon uchun captionni qabul qilish
@dp.message_handler(state=ElonState.caption)
async def get_elon_caption(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    caption = message.text
    await state.update_data(caption=caption)
    
    await message.answer("⏰ E'lonni har kuni yuborish vaqtini kiriting (HH:MM formatida, masalan: 00:01):", reply_markup=btn_cancel)
    await ElonState.time.set()

# E'lon uchun vaqtni qabul qilish va jo'natish
@dp.message_handler(state=ElonState.time)
async def get_elon_time(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    time_text = message.text
    
    # Vaqt formatini tekshirish
    if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time_text) and time_text != "❌ Bekor qilish":
        await message.answer("⚠️ Noto'g'ri vaqt formati. Iltimos, vaqtni HH:MM formatida kiriting (masalan: 00:01):", reply_markup=btn_cancel)
        return
    
    # State'dan ma'lumotlarni olish
    data = await state.get_data()
    
    # Check which type of content we have
    is_text_only = data.get("is_text_only", False)
    is_video = data.get("is_video", False)
    
    if is_text_only:
        text = data.get("text")
        # Here we use the photo field to store a special marker for text posts
        add_post("TEXT_ONLY", text, time_text)
    elif is_video:
        video_id = data.get("video")
        caption = data.get("caption", "")
        # We prefix the ID with "VIDEO:" to distinguish it
        add_post(f"VIDEO:{video_id}", caption, time_text)
    else:
        # Regular photo post
        photo_id = data.get("photo")
        caption = data.get("caption", "")
        add_post(photo_id, caption, time_text)
    
    # Bazadan ohirgi qo'shilgan ID olish
    post_id = cursor.lastrowid
    
    content_type = "matn" if is_text_only else "video" if is_video else "rasm"
    
    await message.answer(
        f"✅ E'lon saqlandi!\n"
        f"🕒 Har kuni soat {time_text} da yuboriladi.\n"
        f"📝 E'lon ID: {post_id}\n"
        f"📄 Kontent turi: {content_type}", 
        reply_markup=btn_start
    )
    
    await state.finish()

# Matn xabarlarni ham qabul qilish (Post uchun)
# @dp.message_handler(state=PostState.photo, content_types=types.ContentType.TEXT)
# async def text_instead_of_photo_post(message: types.Message, state: FSMContext):
#     if not is_admin(message.from_user.id):
#         return
        
#     text = message.text
#     if text != "❌ Bekor qilish":  # Agar "Bekor qilish" bo'lmasa
#         # Check if the message is forwarded
#         if message.forward_from_chat:
#             # Bazadan barcha guruhlarni olish
#             groups = cursor.execute("SELECT group_id, group_name, joined_date FROM active_groups").fetchall()

#             if groups:
#                 sent_count = 0
#                 for group in groups:
#                     group_id, group_name, joined_date = group
#                     try:
#                         await bot.send_message(chat_id=group_id, text=text)
#                         sent_count += 1
#                     except Exception as e:
#                         print(f"⚠️ {group_name} ({group_id}) ga jo'natib bo'lmadi: {e}")

#                 await message.answer(f"📢 {sent_count} ta guruhga forward qilingan matn jo'natildi!", reply_markup=btn_start)
#             else:
#                 await message.answer("❌ Hech qanday aktiv guruh topilmadi.", reply_markup=btn_start)

#             await state.finish()
#         else:
#             # Regular text message to send to all groups
#             groups = cursor.execute("SELECT group_id, group_name, joined_date FROM active_groups").fetchall()

#             if groups:
#                 sent_count = 0
#                 for group in groups:
#                     group_id, group_name, joined_date = group
#                     try:
#                         await bot.send_message(chat_id=group_id, text=text)
#                         sent_count += 1
#                     except Exception as e:
#                         print(f"⚠️ {group_name} ({group_id}) ga jo'natib bo'lmadi: {e}")

#                 await message.answer(f"📢 {sent_count} ta guruhga matnli post jo'natildi!", reply_markup=btn_start)
#             else:
#                 await message.answer("❌ Hech qanday aktiv guruh topilmadi.", reply_markup=btn_start)

#             await state.finish()

@dp.message_handler(state=ElonState.photo, content_types=types.ContentType.TEXT)
async def text_instead_of_photo_elon(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    text = message.text
    if text != "❌ Bekor qilish":  # Agar "Bekor qilish" bo'lmasa
        # Check if the message is forwarded
        if message.forward_from_chat:
            # Reject forwarded messages
            await message.answer("⚠️ E'lon uchun forward qilingan xabarlar qabul qilinmaydi. Iltimos, yangi matn yuboring:", reply_markup=btn_cancel)
            return
        else:
            await state.update_data(is_text_only=True, text=text)
            await message.answer("✍️ Endi qo'shimcha izoh kiriting yoki '⏭ O'tkazish' deb yozing:", reply_markup=btn_cancel)
            await ElonState.caption.set()

@dp.message_handler(content_types=types.ContentType.VIDEO, state=ElonState.photo)
async def handle_video_elon(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    video_id = message.video.file_id
    caption = message.caption or ""
    
    if message.forward_from_chat:
        await state.update_data(video=video_id, caption=caption, is_video=True, is_forwarded=True)
        await message.answer("⏰ E'lonni har kuni yuborish vaqtini kiriting (HH:MM formatida, masalan: 00:01):", reply_markup=btn_cancel)
        await ElonState.time.set()
    else:
        await state.update_data(video=video_id, is_video=True)
        await message.answer("✍️ Endi video uchun izoh (caption) yuboring:", reply_markup=btn_cancel)
        await ElonState.caption.set()

async def send_scheduled_posts():
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Joriy vaqtga rejalashtirilgan barcha e'lonlarni olish
    scheduled_posts = cursor.execute(
        "SELECT id, photo, caption, post_time, status FROM active_posts WHERE post_time LIKE ? AND status = 'active'",
        (f"%{current_time}%",)
    ).fetchall()
    
    if scheduled_posts:
        groups = cursor.execute("SELECT group_id, group_name FROM active_groups").fetchall()
        
        if groups:
            for post in scheduled_posts:
                post_id = post[0]
                media_id = post[1]
                caption = post[2]
                
                # E'lon bugun yuborilganligini tekshirish
                last_sent = cursor.execute(
                    "SELECT last_sent_date FROM post_history WHERE post_id = ?",
                    (post_id,)
                ).fetchone()
                
                # Agar e'lon bugun yuborilgan bo'lsa, o'tkazib yuborish
                if last_sent and last_sent[0] == current_date:
                    print(f"E'lon #{post_id} bugun allaqachon yuborilgan, o'tkazib yuborildi")
                    continue
                
                sent_count = 0
                for group in groups:
                    group_id, group_name = group
                    try:
                        if media_id == "TEXT_ONLY":
                            await bot.send_message(chat_id=group_id, text=caption)
                        elif media_id.startswith("VIDEO:"):
                            video_id = media_id[6:]  
                            await bot.send_video(chat_id=group_id, video=video_id, caption=caption)
                        else:
                            await bot.send_photo(chat_id=group_id, photo=media_id, caption=caption)
                        
                        sent_count += 1
                    except Exception as e:
                        print(f"⚠️ {group_name} ({group_id}) ga {post_id} e'lonni jo'natib bo'lmadi: {e}")
                
                print(f"📊 E'lon #{post_id} {sent_count} ta guruhga yuborildi")
                
                # Bu e'lon oxirgi yuborilgan sanasini yangilash
                mark_post_as_sent(post_id)


async def verify_bot_in_groups():
    groups = cursor.execute("SELECT group_id, group_name FROM active_groups").fetchall()
    for group in groups:
        group_id, group_name = group

        try:
            chat_member = await bot.get_chat_member(group_id, (await bot.get_me()).id)
            if chat_member.status == "left" or chat_member.status == "kicked":
                cursor.execute("DELETE FROM active_groups WHERE group_id = ?", (group_id,))
                connect.commit()

                for admin_id in ADMINS:
                    try:
                        await bot.send_message(
                            admin_id,
                            f"⚠️ Bot {group_name} ({group_id}) guruhida topilmadi!\n"
                            f"✅ Guruh ma'lumotlari bazadan o'chirildi."
                        )
                    except Exception as e:
                        print(f"Admin {admin_id}ga xabar yuborib bo'lmadi: {e}")

        except Exception as e:
            cursor.execute("DELETE FROM active_groups WHERE group_id = ?", (group_id,))
            connect.commit()

            for admin_id in ADMINS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"⚠️ Bot {group_name} ({group_id}) guruhiga kira olmadi: {str(e)}\n"
                        f"✅ Guruh ma'lumotlari bazadan o'chirildi."
                    )
                except Exception as e2:
                    print(f"Admin {admin_id}ga xabar yuborib bo'lmadi: {e2}")
    
async def scheduler():
    daily_check_done = False
    
    while True:
        current_time = datetime.now()
        await send_scheduled_posts()
        
        if current_time.hour == 4 and current_time.minute == 0 and not daily_check_done:
            await verify_bot_in_groups()
            daily_check_done = True
            print(f"📊 Guruhlar tekshirildi: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        elif current_time.hour != 4:
            daily_check_done = False
            
        await asyncio.sleep(60)


@dp.message_handler(content_types=types.ContentType.NEW_CHAT_MEMBERS)
async def join_group(message: types.Message):
    # Bot o'zi qo'shilganligini tekshirish
    bot_info = await bot.get_me()

    for new_member in message.new_chat_members:
        if new_member.id == bot_info.id:
            group_id = str(message.chat.id)
            group_name = message.chat.title
            joined_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Hozirgi vaqtni olish

            # Guruh bor yoki yo'qligini tekshirish
            select = cursor.execute("SELECT group_id FROM active_groups WHERE group_id=?", (group_id,)).fetchone()

            if select:
                cursor.execute("UPDATE active_groups SET group_name=?, joined_date=? WHERE group_id=?",
                               (group_name, joined_date, group_id))
            else:
                cursor.execute("INSERT INTO active_groups (group_id, group_name, joined_date) VALUES (?, ?, ?)",
                               (group_id, group_name, joined_date))

            connect.commit()

            # Faqat admin uchun xabar yuborish
            for admin_id in ADMINS:
                try:
                    # Qo'shgan user haqida ma'lumot
                    added_by_user = message.from_user
                    added_by_name = added_by_user.full_name if added_by_user else "Noma'lum foydalanuvchi"
                    added_by_id = added_by_user.id if added_by_user else "Noma'lum ID"

                    # Check if the user who added the bot is an admin
                    is_user_admin = is_admin(added_by_id)
                    user_status = "admin" if is_user_admin else "oddiy foydalanuvchi"

                    await bot.send_message(
                        admin_id,
                        f"✅ Bot yangi guruhga qo'shildi: {group_name} ({group_id})\n"
                        f"👤 Qo'shgan: {added_by_name} ({added_by_id}) - {user_status}"
                    )
                except Exception as e:
                    print(f"Admin {admin_id}ga xabar yuborib bo'lmadi: {e}")




from aiogram.types import InputMediaPhoto, InputMediaVideo
from collections import defaultdict
import asyncio

post_media_groups = defaultdict(list)
elon_media_groups = defaultdict(list)
post_tasks = {}
elon_tasks = {}

# ==== POST ====
@dp.message_handler(lambda m: m.media_group_id is not None, state=PostState.photo,
                    content_types=types.ContentTypes.ANY)
async def handle_post_media_group(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    post_media_groups[message.media_group_id].append(message)
    if message.media_group_id in post_tasks:
        post_tasks[message.media_group_id].cancel()

    post_tasks[message.media_group_id] = asyncio.create_task(
        process_post_media_group(message.media_group_id, message, state)
    )

async def process_post_media_group(media_group_id, sample_msg, state):
    try:
        await asyncio.sleep(1.5)
        messages = post_media_groups.pop(media_group_id, [])
        post_tasks.pop(media_group_id, None)

        if not messages:
            return

        caption = messages[0].caption or ""
        media = []
        for msg in messages:
            if msg.photo:
                media.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=caption if not media else None))
            elif msg.video:
                media.append(InputMediaVideo(media=msg.video.file_id, caption=caption if not media else None))

        groups = cursor.execute("SELECT group_id FROM active_groups").fetchall()
        for group in groups:
            try:
                await bot.send_media_group(chat_id=group[0], media=media)
            except Exception as e:
                print(f"POST media_group {group[0]}ga yuborilmadi: {e}")

        await sample_msg.answer(f"📢 {len(groups)} ta guruhga media group post yuborildi!", reply_markup=btn_start)
        await state.finish()
    except asyncio.CancelledError:
        pass


@dp.message_handler(lambda m: m.media_group_id is not None, state=ElonState.photo,
                    content_types=types.ContentTypes.ANY)
async def handle_elon_media_group(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    # Check if the message is forwarded
    if message.forward_from_chat:
        # We can only reject the first message of the media group here
        await message.answer("⚠️ E'lon uchun forward qilingan media group qabul qilinmaydi. Iltimos, yangi media yuklang:", reply_markup=btn_cancel)
        return

    elon_media_groups[message.media_group_id].append(message)
    if message.media_group_id in elon_tasks:
        elon_tasks[message.media_group_id].cancel()

    elon_tasks[message.media_group_id] = asyncio.create_task(
        process_elon_media_group(message.media_group_id, message, state)
    )

async def process_elon_media_group(media_group_id, sample_msg, state):
    try:
        await asyncio.sleep(1.5)
        messages = elon_media_groups.pop(media_group_id, [])
        elon_tasks.pop(media_group_id, None)

        if not messages:
            return

        caption = messages[0].caption or ""
        media = []
        for msg in messages:
            if msg.photo:
                media.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=caption if not media else None))
            elif msg.video:
                media.append(InputMediaVideo(media=msg.video.file_id, caption=caption if not media else None))

        await state.update_data(media_group=media, caption=caption, is_media_group=True)
        await sample_msg.answer("⏰ E'lonni har kuni yuborish vaqtini kiriting (HH:MM formatida, masalan: 00:01):", reply_markup=btn_cancel)
        await ElonState.time.set()
    except asyncio.CancelledError:
        pass

async def on_startup(_):
    asyncio.create_task(scheduler())
    print("Bot va scheduler ishga tushdi!")

    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, "🚀 Bot qayta ishga tushirildi va faqat admin uchun ishlaydi!")
        except Exception as e:
            print(f"Admin {admin_id}ga xabar yuborib bo'lmadi: {e}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
# kino_bot.py
import json
import asyncio
from datetime import datetime, timedelta

from fastapi import FastAPI
import uvicorn

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

# ================== CONFIG ==================
BOT_TOKEN = "8544683801:AAGrRNaeYQ418IRymUR4d6qObHunc5SmGxU"
OWNER_ID = 8297497276
CHANNEL_LINK = "https://t.me/kino_2026_premyera"

# Ma'lumotlar fayllari
USERS_FILE = "users.json"
KINO_FILE = "kino.json"
ADMINS_FILE = "admins.json"

# ================== INIT BOT ==================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# ================== FSM STATES ==================
class KinoUpload(StatesGroup):
    waiting_code = State()
    waiting_name = State()
    waiting_info = State()
    waiting_video = State()

class PremiumGive(StatesGroup):
    waiting_user_id = State()

class AdminManage(StatesGroup):
    waiting_user_id = State()

# ================== UTILS ==================
def load_json(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def get_menu(user_id):
    """Dynamic menu"""
    users = load_json(USERS_FILE)
    tarif = users.get(str(user_id), {}).get("tarif", "oddiy")
    admins = load_json(ADMINS_FILE).get("admins", [])
    
    buttons = [
        [KeyboardButton(text="🎬 Kino kodi orqali qidirish")],
        [KeyboardButton(text="⭐ Premium faollashtirish")]
    ]
    if user_id in admins:
        buttons.append([KeyboardButton(text="⚙ Admin paneli")])
    buttons.append([KeyboardButton(text="🧾 Mening hisobim")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ================== START ==================
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Assalomu alaykum! Botimizga hush kelibsiz 😊",
        reply_markup=get_menu(message.from_user.id)
    )

# ================== KINO QIDIRISH ==================
@dp.message(F.text == "🎬 Kino kodi orqali qidirish")
async def search_kino(message: types.Message, state: FSMContext):
    await message.answer("Iltimos kino kodini kiriting (raqamlar):")
    await state.set_state(KinoUpload.waiting_code)

@dp.message(KinoUpload.waiting_code)
async def process_kino_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    if not code.isdigit():
        await message.answer("❌ Kod raqamlardan iborat bo‘lishi kerak. Qaytadan kiriting:")
        return
    kino_db = load_json(KINO_FILE)
    if code not in kino_db:
        await message.answer("❌ Kino topilmadi!")
        await state.clear()
        return
    # Kino mavjud
    kino = kino_db[code]
    users = load_json(USERS_FILE)
    user = users.get(str(message.from_user.id), {"tarif": "oddiy"})
    premium = user.get("tarif", "oddiy") == "premium"
    
    # Kino yuborish
    video = kino.get("video")
    name = kino.get("name")
    info = kino.get("info")
    text = f"Kino nomi: {name}\nKino haqida: {info}\nKino kodi: {code}"
    
    if premium:
        await message.answer_video(video, caption=text)
    else:
        await message.answer_video(video, caption=text)
        await message.answer("❌ Oddiy foydalanuvchilar kino yuklab olish, nusxalash va uzatish imkoniga ega emaslar.")

    await state.clear()

# ================== PREMIUM FAOLLASHTIRISH ==================
@dp.message(F.text == "⭐ Premium faollashtirish")
async def premium_info(message: types.Message, state: FSMContext):
    await message.answer(
        "Siz bizning botimizning Premium tarifidan foydalanmoqchisiz\n\n"
        "Afzalliklari:\n"
        "1. Kino yuklash va nusxalash imkoniyati\n"
        "2. Hech qanday obunalarsiz foydalanish\n"
        "3. Oddiy tariflarda yo‘q yangi kinolar\n\n"
        "Tariflar:\n30 kun - 20.000 UZS\n\n"
        "Premium berish faqat adminlar orqali amalga oshiriladi."
    )

# ================== MENING HISOBIM ==================
@dp.message(F.text == "🧾 Mening hisobim")
async def my_account(message: types.Message):
    users = load_json(USERS_FILE)
    user = users.get(str(message.from_user.id), {"name": message.from_user.full_name, "tarif": "oddiy"})
    tarif = user.get("tarif", "oddiy")
    if tarif == "premium":
        end_date = user.get("premium_end")
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
        days_left = (end_date_dt - datetime.now()).days
        days_left = max(days_left, 0)
        msg = f"Foydalanuvchi ismi: {user.get('name')}\nTarifi: premium\nVaqti: {days_left} kun qolgan"
    else:
        msg = f"Foydalanuvchi ismi: {user.get('name')}\nTarifi: oddiy\nVaqti: doimiy"
    await message.answer(msg)

# ================== ADMIN PANEL ==================
@dp.message(F.text == "⚙ Admin paneli")
async def admin_panel(message: types.Message):
    admins = load_json(ADMINS_FILE).get("admins", [])
    if message.from_user.id not in admins:
        await message.answer("❌ Sizga ruxsat yo‘q")
        return
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Kino yuklash")],
            [KeyboardButton(text="⭐ Premium berish")],
            [KeyboardButton(text="🛠 Admin qo‘shish/olib tashlash")],
            [KeyboardButton(text="↩ Orqaga")]
        ],
        resize_keyboard=True
    )
    await message.answer("Admin paneliga hush kelibsiz", reply_markup=kb)

# ================== FastAPI run ==================
@app.get("/")
def home():
    return {"status": "Bot ishlayapti"}

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

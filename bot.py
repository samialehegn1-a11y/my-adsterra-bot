import asyncio
import logging
import sys
import re
import time
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import init_db, add_user, get_user, check_and_reset_daily_ads, increment_ad, reset_balance

# --- እባክዎ እነዚህን መረጃዎች በትክክል ይሙሉ ---
TOKEN = "8517362183:AAE5NEmb2QphoprzEQMeJ3dsdloIPcV2-0k"
ADSTERRA_LINK = "https://www.profitableratecpmnetwork.com/e61qyxn3ya?key=082792f8dcc56b647c08e3e9ed8aa7e5"

# 1 እስከ 3 ያሉት ቻናሎች በግዴታ (Forced) የሚታዩ ሲሆኑ፣ 4ተኛው መደበኛ ሆኖ በድብቅ ይካተታል
CHANNELS = [
    {"name": "ቻናል 1", "url": "https://t.me/videobestquality", "id": "@channel_1_username", "forced": True},
    {"name": "ቻናል 2", "url": "https://t.me/Big_Tech_sami", "id": "@channel_2_username", "forced": True},
    {"name": "ቻናል 3", "url": "https://t.me/ethiotech011", "id": "@channel_3_username", "forced": True},
    {"name": "ቻናል 4", "url": "https://t.me/ETHIO_FREE_INTER", "id": "@channel_4_username", "forced": False}
]

PROOF_CHANNEL_ID = -1003774219402

bot = Bot(token=TOKEN)
dp = Dispatcher()

class WithdrawState(StatesGroup):
    waiting_for_phone = State()

async def check_subscriptions(user_id: int) -> bool:
    for ch in CHANNELS:
        if ch["forced"]:  # ግዴታ የሆኑትን 3 ቻናሎች ብቻ እንፈትሻለን
            try:
                member = await bot.get_chat_member(chat_id=ch["id"], user_id=user_id)
                if member.status in ["left", "kicked"]:
                    return False
            except Exception:
                pass
    return True

def get_join_keyboard():
    keyboard = []
    for ch in CHANNELS:
        if ch["forced"]:  # በግዴታ መታየት የሚገባቸውን ቁልፎች ብቻ ለተጠቃሚው እናሳያለን
            keyboard.append([InlineKeyboardButton(text=f"📢 {ch['name']} መቀላቀያ", url=ch["url"])])
    keyboard.append([InlineKeyboardButton(text="✅ አባል ሆጫለሁ (Verify)", callback_data="check_join")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 አካውንት (Balance)", callback_data="balance"),
         InlineKeyboardButton(text="👥 ጓደኛጋብዝ (Referral)", callback_data="referral")],
        [InlineKeyboardButton(text="📺 ማስታወቂያ እይ (+1 ብር)", callback_data="watch_ad"),
         InlineKeyboardButton(text="📤 ገንዘብ አውጣ (Withdraw)", callback_data="withdraw")]
    ])

@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        parsed_id = int(args[1])
        if parsed_id != message.from_user.id:
            referrer_id = parsed_id

    await add_user(message.from_user.id, referrer_id)

    is_joined = await check_subscriptions(message.from_user.id)
    if not is_joined:
        await message.answer(
            "⚠️ <b>Regl Pay</b> ቦቱን ለመጠቀም መጀመሪያ ከታች ያሉትን <b>ቻናሎች</b> መቀላቀል አለብዎት!",
            reply_markup=get_join_keyboard(),
            parse_html=True
        )
        return

    await message.answer(
        f"👋 ሰላም <b>{message.from_user.first_name}</b> ወደ <b>Regl Pay</b> እንኳን በደህና መጡ!\n\n"
        "ይህ ቦት ጓደኞችን በመጋበዝ እና ማስታወቂያዎችን በማየት ብር የሚሠሩበት ነው። ከታች ያሉትን አማራጮች ይጠቀሙ፦",
        reply_markup=main_menu(),
        parse_html=True
    )

@dp.callback_query(F.data == "check_join")
async def verify_join(callback: CallbackQuery):
    is_joined = await check_subscriptions(callback.from_user.id)
    if not is_joined:
        await callback.answer("❌ ግዴታ የሆኑትን ቻናሎች ገና አልቀላቀሉም!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎉 እናመሰግናለን! ቻናሎቹን በተሳካ ሁኔታ ተቀላቅለዋል። አሁን <b>Regl Pay</b> ቦቱን መጠቀም ይችላሉ፦",
        reply_markup=main_menu(),
        parse_html=True
    )
    await callback.answer()

@dp.callback_query(F.data == "balance")
async def check_balance(callback: CallbackQuery):
    if not await check_subscriptions(callback.from_user.id):
        await callback.message.edit_text("⚠️ እባክዎ መጀመሪያ ቻናሎቻችንን ይቀላቀሉ!", reply_markup=get_join_keyboard())
        return

    user_data = await get_user(callback.from_user.id)
    balance = user_data[0] if user_data else 0.0
    ads = user_data[1] if user_data else 0
    refs = user_data[4] if user_data else 0

    await callback.message.edit_text(
        f"💳 <b>የ Regl Pay አካውንት መረጃዎ</b>\n\n"
        f"💰 ቀሪ ሂሳብ: <b>{balance} ብር</b>\n"
        f"📺 አጠቃላይ ያዩዋቸው ማስታወቂያዎች: <b>{ads}</b>\n"
        f"👥 የጋበዟቸው ሰዎች: <b>{refs} ሰው</b>",
        reply_markup=main_menu(),
        parse_html=True
    )
    await callback.answer()

@dp.callback_query(F.data == "referral")
async def referral_link(callback: CallbackQuery):
    if not await check_subscriptions(callback.from_user.id):
        await callback.message.edit_text("⚠️ እባክዎ መጀመሪያ ቻናሎቻችንን ይቀላቀሉ!", reply_markup=get_join_keyboard())
        return

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={callback.from_user.id}"
    await callback.message.edit_text(
        f"👥 <b>የ Regl Pay ሪፈራል ሊንክዎ</b>\n\n"
        f"ይህንን ሊንክ በመጠቀም ሰዎችን ወደ ቦቱ ሲጋብዙ <b>2 ብር</b> ያገኛሉ!\n\n"
        f"🔗 ሊንክዎ:\n<code>{ref_link}</code>",
        reply_markup=main_menu(),
        parse_html=True
    )
    await callback.answer()

@dp.callback_query(F.data == "watch_ad")
async def watch_ad(callback: CallbackQuery):
    if not await check_subscriptions(callback.from_user.id):
        await callback.message.edit_text("⚠️ እባክዎ መጀመሪያ ቻናሎቻችንን ይቀላቀሉ!", reply_markup=get_join_keyboard())
        return

    user_id = callback.from_user.id
    daily_ads, last_time = await check_and_reset_daily_ads(user_id)

    if daily_ads >= 10:
        current_time = time.time()
        time_left = int(86400 - (current_time - last_time))
        hours_left = time_left // 3600
        minutes_left = (time_left % 3600) // 60
        
        await callback.answer(
            f"❌ የዛሬውን የ 10 ማስታወቂያ ገደብ ጨርሰዋል!\n"
            f"እባክዎ ቀጣይ ማስታወቂያ ለማየት {hours_left} ሰዓት ከ {minutes_left} ደቂቃ ይጠብቁ።",
            show_alert=True
        )
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📺 ማስታወቂያውን ለማየት እዚህ ይጫኑ", url=ADSTERRA_LINK)],
        [InlineKeyboardButton(text="✅ ማስታወቂያ አይቼጨርሻለሁ (1 ብር ውሰድ)", callback_data="claim_reward")]
    ])
    
    await callback.message.edit_text(
        f"📺 <b>ማስታወቂያ ማየት (የዛሬ: {daily_ads}/10)</b>\n\n"
        "1. ከታች ያለውን ሊንክ በመጫን ማስታወቂያውን ይመልከቱ።\n"
        "2. ማስታወቂያውን አይተው ሲጨርሱ <b>'ማስታወቂያ አይቼጨርሻለሁ'</b> የሚለውን በመጫን 1 ብርዎን ይውሰዱ!",
        reply_markup=keyboard,
        parse_html=True
    )
    await callback.answer()

@dp.callback_query(F.data == "claim_reward")
async def claim_reward(callback: CallbackQuery):
    user_id = callback.from_user.id
    daily_ads, _ = await check_and_reset_daily_ads(user_id)

    if daily_ads >= 10:
        await callback.message.edit_text(
            "❌ የዛሬው ገደብ አልቋል! ነገ እንደገና መሞከር ይችላሉ።",
            reply_markup=main_menu(),
            parse_html=True
        )
        await callback.answer("ገደብ አልቋል!", show_alert=True)
        return

    await increment_ad(user_id)
    await callback.message.edit_text(
        "🎉 እናመሰግናለን! ማስታወቂያውን በማየትዎ <b>1.00 ብር</b> ወደ አካውንትዎ ገብቷል።",
        reply_markup=main_menu(),
        parse_html=True
    )
    await callback.answer("1 ብር ተጨምሯል!")

@dp.callback_query(F.data == "withdraw")
async def withdraw_request(callback: CallbackQuery, state: FSMContext):
    if not await check_subscriptions(callback.from_user.id):
        await callback.message.edit_text("⚠️ እባክዎ መጀመሪያ ቻናሎቻችንን ይቀላቀሉ!", reply_markup=get_join_keyboard())
        return

    user_data = await get_user(callback.from_user.id)
    balance = user_data[0] if user_data else 0.0
    ads = user_data[1] if user_data else 0
    refs = user_data[4] if user_data else 0

    if balance < 30.0 or ads < 30 or refs < 10:
        await callback.answer(
            f"❌ ገንዘብ ለማውጣት የሚከተሉትን ማሟላት አለብዎት፡\n"
            f"• ቢያንስ 30 ብር ሊኖርዎት ይገባል (አሁን: {balance} ብር)\n"
            f"• በትንሹ 30 ማስታወቂያ ማየት አለብዎት (አሁን: {ads})\n"
            f"• በትንሹ 10 ሰው መጋበዝ አለብዎት (አሁን: {refs} ሰው)",
            show_alert=True
        )
        return

    await state.set_state(WithdrawState.waiting_for_phone)
    await callback.message.edit_text(
        "📤 <b>የገንዘብ ማውጫ ጥያቄ (Regl Pay)</b>\n\n"
        "እባክዎ የTelebirr አካውንትዎን ያስገቡ፦",
        parse_html=True
    )
    await callback.answer()

@dp.message(WithdrawState.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()

    if phone.startswith("07"):
        await message.answer("❌ እባክዎ የEthio telecom ስልክ ቁጥር (በ 09 የሚጀምር) ብቻ ያስገቡ!")
        return

    if not re.match(r"^09\d{8}$", phone):
        await message.answer("❌ ትክክል ያልሆነ ስልክ አስገብተዋል! እባክዎ ትክክለኛ የEthio telecom ስልክ ቁጥር (ለምሳሌ: 0911223344) ብቻ ያስገቡ።")
        return

    user_data = await get_user(message.from_user.id)
    balance = user_data[0]

    try:
        proof_text = (
            f"✅ **Regl Pay - አዲስ የክፍያ ጥያቄ!**\n\n"
            f"👤 ተጠቃሚ: {message.from_user.full_name} (@{message.from_user.username or 'নেই'})\n"
            f"🆔 ዩዘር ID: `{message.from_user.id}`\n"
            f"💸 የተጠየቀው መጠን: **{balance} ብር**\n"
            f"📞 ቴሌብር ቁጥር: `{phone}`"
        )
        await bot.send_message(chat_id=PROOF_CHANNEL_ID, text=proof_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Proof ቻናል ላይ መለጠፍ አልተቻለም: {e}")

    await reset_balance(message.from_user.id)
    await state.clear()

    await message.answer(
        "🎉 የገንዘብ ማውጫ ጥያቄዎ በትክክል ወደ <b>Regl Pay</b> አስተዳዳሪዎች ተልኳል!\n"
        "አረጋግጠው በቅርቡ ይለቁልዎታል። እናመሰግናለን! 🙏",
        reply_markup=main_menu(),
        parse_html=True
    )

async def main():
    await init_db()
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

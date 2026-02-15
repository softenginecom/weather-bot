#!/usr/bin/env python3
"""
🌤️ Telegram Ob-havo Bot
Kerakli kutubxonalar:
    pip install python-telegram-bot requests

Sozlash:
    1. @BotFather dan BOT_TOKEN oling
    2. openweathermap.org dan bepul WEATHER_API_KEY oling
    3. Quyidagi TOKEN va API_KEY ni o'zingiznikiga almashtiring
"""

import logging
import requests
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ─── SOZLAMALAR ───────────────────────────────────────────────────────────────
BOT_TOKEN = "8259707562:AAFMtypXdU_0nZHvN1mb3BpQPRUcY5OuW-g"          # @BotFather dan olgan tokeningiz
WEATHER_API_KEY = "702d3ca5322f7b2a3776940e8f58e3b3"  # openweathermap.org API kaliti
BASE_URL = "https://api.openweathermap.org/data/2.5"

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── OB-HAVO IKONKALARI ───────────────────────────────────────────────────────
WEATHER_ICONS = {
    "Clear": "☀️",
    "Clouds": "☁️",
    "Rain": "🌧️",
    "Drizzle": "🌦️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
    "Mist": "🌫️",
    "Fog": "🌫️",
    "Haze": "🌫️",
    "Smoke": "🌫️",
    "Dust": "🌪️",
    "Sand": "🌪️",
    "Tornado": "🌪️",
}

# ─── YORDAMCHI FUNKSIYALAR ────────────────────────────────────────────────────

def get_icon(condition: str) -> str:
    return WEATHER_ICONS.get(condition, "🌡️")


def wind_direction(degrees: float) -> str:
    dirs = ["↑ Shimol", "↗ Shimoli-Sharq", "→ Sharq", "↘ Janubi-Sharq",
            "↓ Janub", "↙ Janubi-G'arb", "← G'arb", "↖ Shimoli-G'arb"]
    return dirs[round(degrees / 45) % 8]


def format_current_weather(data: dict) -> str:
    city = data["name"]
    country = data["sys"]["country"]
    temp = round(data["main"]["temp"])
    feels = round(data["main"]["feels_like"])
    humidity = data["main"]["humidity"]
    wind_speed = round(data["wind"]["speed"] * 3.6, 1)  # m/s → km/h
    wind_deg = data["wind"].get("deg", 0)
    pressure = data["main"]["pressure"]
    visibility = data.get("visibility", 0) // 1000  # metr → km
    condition = data["weather"][0]["main"]
    description = data["weather"][0]["description"].capitalize()
    icon = get_icon(condition)
    sunrise = datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M")
    sunset = datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M")

    return (
        f"{icon} *{city}, {country}* — Hozirgi ob-havo\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌡️ Harorat: *{temp}°C* (his: {feels}°C)\n"
        f"🌤️ Holat: {description}\n"
        f"💧 Namlik: {humidity}%\n"
        f"💨 Shamol: {wind_speed} km/soat {wind_direction(wind_deg)}\n"
        f"🔵 Bosim: {pressure} hPa\n"
        f"👁️ Ko'rinish: {visibility} km\n"
        f"🌅 Quyosh chiqishi: {sunrise}\n"
        f"🌇 Quyosh botishi: {sunset}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 _{datetime.now().strftime('%d.%m.%Y %H:%M')}_"
    )


def format_forecast(data: dict) -> str:
    city = data["city"]["name"]
    country = data["city"]["country"]
    lines = [f"📅 *{city}, {country}* — 5 kunlik prognoz\n━━━━━━━━━━━━━━━━━━━━━"]

    daily = {}
    for item in data["list"]:
        date = datetime.fromtimestamp(item["dt"]).strftime("%d.%m.%Y")
        if date not in daily:
            daily[date] = []
        daily[date].append(item)

    days_uz = ["Dush", "Sesh", "Chor", "Pay", "Jum", "Shan", "Yak"]

    for date, items in list(daily.items())[:5]:
        temps = [i["main"]["temp"] for i in items]
        min_t = round(min(temps))
        max_t = round(max(temps))
        condition = items[len(items)//2]["weather"][0]["main"]
        icon = get_icon(condition)
        desc = items[len(items)//2]["weather"][0]["description"].capitalize()
        humidity = round(sum(i["main"]["humidity"] for i in items) / len(items))
        wind = round(max(i["wind"]["speed"] for i in items) * 3.6, 1)

        dt = datetime.strptime(date, "%d.%m.%Y")
        day_name = days_uz[dt.weekday()]

        lines.append(
            f"\n{icon} *{date}* ({day_name})\n"
            f"   🌡️ {min_t}°C ~ {max_t}°C  |  {desc}\n"
            f"   💧 {humidity}%  💨 {wind} km/soat"
        )

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


# ─── API SO'ROVLARI ───────────────────────────────────────────────────────────

def fetch_current(city: str = None, lat: float = None, lon: float = None) -> dict | None:
    params = {"appid": WEATHER_API_KEY, "units": "metric", "lang": "uz"}
    if city:
        params["q"] = city
    else:
        params["lat"] = lat
        params["lon"] = lon
    try:
        resp = requests.get(f"{BASE_URL}/weather", params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.RequestException:
        return None


def fetch_forecast(city: str = None, lat: float = None, lon: float = None) -> dict | None:
    params = {"appid": WEATHER_API_KEY, "units": "metric", "lang": "uz", "cnt": 40}
    if city:
        params["q"] = city
    else:
        params["lat"] = lat
        params["lon"] = lon
    try:
        resp = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.RequestException:
        return None


# ─── KLAVIATURA ───────────────────────────────────────────────────────────────

def main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("🌤️ Hozirgi ob-havo"), KeyboardButton("📅 5 kunlik prognoz")],
        [KeyboardButton("📍 Joylashuvim orqali"), KeyboardButton("🏙️ Shahar qidirish")],
        [KeyboardButton("ℹ️ Yordam")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def weather_type_keyboard(lat: float, lon: float) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🌤️ Hozir", callback_data=f"cur|{lat}|{lon}"),
            InlineKeyboardButton("📅 5 kun", callback_data=f"fore|{lat}|{lon}"),
        ],
        [
            InlineKeyboardButton("🔙 Orqaga", callback_data="back|main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# ─── HANDLER FUNKSIYALAR ──────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Salom, *{name}*!\n\n"
        "Men sizga ob-havo ma'lumotlarini beraman 🌍\n\n"
        "🔹 Shahar nomini yozing\n"
        "🔹 Yoki joylashuvingizni yuboring\n"
        "🔹 Tugmalardan foydalaning\n\n"
        "Quyidagi menyudan tanlang:",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Yordam*\n\n"
        "🌤️ *Hozirgi ob-havo* — Shahar harorati, shamol, namlik\n"
        "📅 *5 kunlik prognoz* — Keyingi 5 kunlik bashorat\n"
        "📍 *Joylashuvim orqali* — GPS koordinatangiz bo'yicha\n"
        "🏙️ *Shahar qidirish* — Istalgan shahar nomini kiriting\n\n"
        "💡 *Maslahat:* Shunchaki shahar nomini yozsangiz ham ishlaydi!\n"
        "Masalan: `Toshkent`, `London`, `Dubai`",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Tugma bosilganda
    if text == "🌤️ Hozirgi ob-havo":
        context.user_data["mode"] = "current"
        last_city = context.user_data.get("last_city")
        if last_city:
            msg = (
                f"🏙️ Shahar nomini kiriting:\n"
                f"_(Masalan: Toshkent, Samarqand, Moscow)_\n\n"
                f"💾 Oxirgi shahar: *{last_city}*"
            )
        else:
            msg = "🏙️ Shahar nomini kiriting:\n_(Masalan: Toshkent, Samarqand, Moscow)_"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    if text == "📅 5 kunlik prognoz":
        context.user_data["mode"] = "forecast"
        last_city = context.user_data.get("last_city")
        if last_city:
            msg = (
                f"🏙️ Shahar nomini kiriting:\n"
                f"_(Masalan: Toshkent, Samarqand, Moscow)_\n\n"
                f"💾 Oxirgi shahar: *{last_city}*"
            )
        else:
            msg = "🏙️ Shahar nomini kiriting:\n_(Masalan: Toshkent, Samarqand, Moscow)_"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    if text == "📍 Joylashuvim orqali":
        keyboard = [
            [KeyboardButton("📍 Joylashuvni yuborish", request_location=True)],
            [KeyboardButton("🔙 Orqaga")],
        ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "📍 Joylashuvingizni yuboring:",
            reply_markup=markup,
        )
        return

    if text == "🔙 Orqaga":
        await update.message.reply_text(
            "🏠 Asosiy menyu:",
            reply_markup=main_keyboard(),
        )
        context.user_data.clear()
        return

    if text == "🏙️ Shahar qidirish":
        context.user_data["mode"] = "search"
        last_city = context.user_data.get("last_city")
        if last_city:
            msg = (
                f"🔍 Qaysi shaharni qidiramiz?\n"
                f"_(Masalan: Buxoro, New York, Tokyo)_\n\n"
                f"💾 Oxirgi shahar: *{last_city}*"
            )
        else:
            msg = "🔍 Qaysi shaharni qidiramiz?\n_(Masalan: Buxoro, New York, Tokyo)_"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    if text == "ℹ️ Yordam":
        await help_command(update, context)
        return

    # Shahar nomi kiritildi — ob-havo ko'rsatish
    mode = context.user_data.get("mode", "current")
    # Shahar nomini eslab qoling
    context.user_data["last_city"] = text
    await fetch_and_send(update, context, city=text, mode=mode)
    context.user_data["mode"] = "current"  # reset


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.location
    lat, lon = location.latitude, location.longitude

    await update.message.reply_text(
        "📍 Joylashuvingiz topildi! Qaysi ma'lumot kerak?",
        reply_markup=weather_type_keyboard(lat, lon),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|")
    action = parts[0]

    # Orqaga tugmasi
    if action == "back":
        await query.edit_message_text(
            "🏠 Asosiy menyuga qaytdingiz.\nQuyidagi tugmalardan foydalaning:",
        )
        return

    lat, lon = float(parts[1]), float(parts[2])

    if action == "cur":
        data = fetch_current(lat=lat, lon=lon)
        if data:
            keyboard = [
                [InlineKeyboardButton("📅 5 kunlik prognoz", callback_data=f"fore|{lat}|{lon}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back|main")],
            ]
            await query.edit_message_text(
                format_current_weather(data),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await query.edit_message_text("❌ Ma'lumot olishda xatolik yuz berdi.")
    elif action == "fore":
        data = fetch_forecast(lat=lat, lon=lon)
        if data:
            keyboard = [
                [InlineKeyboardButton("🌤️ Hozirgi ob-havo", callback_data=f"cur|{lat}|{lon}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back|main")],
            ]
            await query.edit_message_text(
                format_forecast(data),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await query.edit_message_text("❌ Ma'lumot olishda xatolik yuz berdi.")


async def fetch_and_send(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    city: str,
    mode: str = "current",
):
    msg = await update.message.reply_text("⏳ Ma'lumot yuklanmoqda...")

    if mode == "forecast":
        data = fetch_forecast(city=city)
        if data:
            keyboard = [
                [InlineKeyboardButton("🌤️ Hozirgi ob-havo", callback_data=f"cur|{data['city']['coord']['lat']}|{data['city']['coord']['lon']}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back|main")],
            ]
            await msg.edit_text(format_forecast(data), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await msg.edit_text(
                f"❌ *{city}* shahri topilmadi.\n"
                "To'g'ri yozilganligini tekshiring.",
                parse_mode="Markdown",
            )
    else:
        data = fetch_current(city=city)
        if data:
            text = format_current_weather(data)
            keyboard = [
                [InlineKeyboardButton("📅 5 kunlik prognozni ko'rish", callback_data=f"fore|{data['coord']['lat']}|{data['coord']['lon']}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back|main")],
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await msg.edit_text(text, parse_mode="Markdown", reply_markup=markup)
        else:
            await msg.edit_text(
                f"❌ *{city}* shahri topilmadi.\n"
                "To'g'ri yozilganligini tekshiring.",
                parse_mode="Markdown",
            )


# ─── ASOSIY FUNKSIYA ──────────────────────────────────────────────────────────

def main():
    print("🤖 Ob-havo bot ishga tushmoqda...")

    app = Application.builder().token(BOT_TOKEN).build()

    # Handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

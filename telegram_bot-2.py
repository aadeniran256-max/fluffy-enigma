"""
TelegramModeratorBot - single file edition (for Pydroid / mobile use)

Setup:
  1. pip install "python-telegram-bot[job-queue]" requests   (use Pydroid's Pip tab)
  2. Paste your real token into BOT_TOKEN below.
  3. Run this file.

Don't share this file once your token is in it - treat it like a password.
If this token (or the old one from earlier) was ever posted publicly,
revoke it in @BotFather with /revoke and generate a new one.
"""

import datetime
import random

import requests
from telegram import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ============================== CONFIG ==============================

BOT_TOKEN = "PASTE_YOUR_TOKEN_HERE"          # from @BotFather
WEATHER_API_KEY = ""                          # optional, from openweathermap.org

# ============================== STORAGE ==============================
# In-memory only - resets when the bot restarts.

warnings = {}           # {user_id: warning_count}
pending_targets = {}    # {user_id: display_name}, used by confirm buttons

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I would tell a UDP joke, but you might not get it.",
    "There are 10 types of people: those who understand binary and those who don't.",
]

QUOTES = [
    "The only way to do great work is to love what you do.",
    "Success is not final, failure is not fatal.",
    "Believe you can and you're halfway there.",
]

GREETING_WORDS = {"hi", "hello", "hey", "yo", "sup"}

# Conversation states
ASK_CITY, ASK_REMIND_TEXT, ASK_REMIND_TIME = range(3)

# ============================== KEYBOARDS ==============================


def main_menu():
    rows = [
        [InlineKeyboardButton("🎉 Fun & Utility", callback_data="menu:fun")],
        [InlineKeyboardButton("👮 Admin Tools", callback_data="menu:admin")],
        [InlineKeyboardButton("🔗 Social", callback_data="menu:social")],
        [InlineKeyboardButton("🖼 Images", callback_data="menu:images")],
        [InlineKeyboardButton("ℹ️ About", callback_data="menu:about")],
    ]
    return InlineKeyboardMarkup(rows)


def back_button(target="menu:main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=target)]])


def fun_menu():
    rows = [
        [
            InlineKeyboardButton("😂 Joke", callback_data="act:joke"),
            InlineKeyboardButton("💬 Quote", callback_data="act:quote"),
        ],
        [
            InlineKeyboardButton("🎲 Roll dice", callback_data="act:roll"),
            InlineKeyboardButton("🪙 Flip coin", callback_data="act:flip"),
        ],
        [
            InlineKeyboardButton("🕒 Time", callback_data="act:time"),
            InlineKeyboardButton("☁️ Weather", callback_data="act:weather"),
        ],
        [InlineKeyboardButton("⏰ Set a reminder", callback_data="act:remind")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(rows)


def images_menu():
    rows = [
        [
            InlineKeyboardButton("🐱 Cat", callback_data="act:cat"),
            InlineKeyboardButton("🐶 Dog", callback_data="act:dog"),
        ],
        [InlineKeyboardButton("🤖 Bot logo", callback_data="act:logo")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(rows)


def social_menu():
    rows = [
        [
            InlineKeyboardButton("🎵 Spotify", callback_data="act:spotify"),
            InlineKeyboardButton("▶️ YouTube", callback_data="act:youtube"),
        ],
        [InlineKeyboardButton("🎬 Movie link", callback_data="act:movie")],
        [
            InlineKeyboardButton("📤 Share bot", callback_data="act:share"),
            InlineKeyboardButton("➕ Invite link", callback_data="act:invite"),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(rows)


def admin_menu():
    rows = [
        [InlineKeyboardButton("✅ Am I admin?", callback_data="act:admincheck")],
        [InlineKeyboardButton("ℹ️ How moderation works", callback_data="act:modhelp")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(rows)


def confirm_action(action, user_id):
    rows = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm:{action}:{user_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="confirm:cancel"),
        ]
    ]
    return InlineKeyboardMarkup(rows)


async def reply_anywhere(update: Update, text: str, **kwargs):
    """Works whether triggered by a /command or a button tap."""
    if update.message:
        await update.message.reply_text(text, **kwargs)
    else:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, **kwargs)


# ============================== GENERAL ==============================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *TelegramModeratorBot* is online!\n\nTap a category to get started:",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I was built in Python using python-telegram-bot!")


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I am active! 💯")


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    target = query.data.split(":", 1)[1]

    menus = {
        "main": ("Choose a category:", main_menu()),
        "fun": ("🎉 *Fun & Utility*", fun_menu()),
        "admin": ("👮 *Admin Tools*\n(admin-only actions require you to be a group admin)", admin_menu()),
        "social": ("🔗 *Social*", social_menu()),
        "images": ("🖼 *Images*", images_menu()),
        "about": (
            "I'm built with python-telegram-bot. I moderate groups, fetch fun "
            "stuff, and remember what you're doing mid-conversation.",
            back_button(),
        ),
    }
    text, markup = menus[target]
    await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip().lower()
    if text in GREETING_WORDS:
        await update.message.reply_text("Hey! Type /start to see what I can do.", reply_markup=main_menu())
    else:
        await update.message.reply_text("Not sure what to do with that — tap /start for a menu of commands.")


# ============================== FUN / UTILITY ==============================


async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_anywhere(update, random.choice(JOKES))


async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_anywhere(update, random.choice(QUOTES))


async def roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_anywhere(update, f"🎲 You rolled: {random.randint(1, 6)}")


async def flip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_anywhere(update, f"🪙 {random.choice(['Heads', 'Tails'])}!")


async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    await reply_anywhere(update, f"Current time: {now}")


async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expression = " ".join(context.args) if context.args else None
    if not expression:
        await reply_anywhere(update, "Usage: /calc 5*3")
        return
    try:
        allowed = set("0123456789+-*/(). ")
        if not set(expression) <= allowed:
            raise ValueError("disallowed characters")
        result = eval(expression, {"__builtins__": {}})
        await reply_anywhere(update, f"Result: {result}")
    except Exception:
        await reply_anywhere(update, "Invalid expression. Example: /calc 5*3")


async def cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = requests.get("https://api.thecatapi.com/v1/images/search", timeout=5).json()
        url = data[0]["url"]
        target = update.message or update.callback_query.message
        if update.callback_query:
            await update.callback_query.answer()
        await target.reply_photo(photo=url, caption="🐱 Random cat!")
    except Exception:
        await reply_anywhere(update, "Couldn't fetch a cat right now, try again in a bit.")


async def dog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = requests.get("https://api.thedogapi.com/v1/images/search", timeout=5).json()
        url = data[0]["url"]
        target = update.message or update.callback_query.message
        if update.callback_query:
            await update.callback_query.answer()
        await target.reply_photo(photo=url, caption="🐶 Random dog!")
    except Exception:
        await reply_anywhere(update, "Couldn't fetch a dog right now, try again in a bit.")


async def logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message or update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer()
    await target.reply_photo(
        photo="https://example.com/your-image.jpg",  # replace with your own image URL
        caption="🤖 TelegramModeratorBot",
    )


# ---- Weather conversation ----

async def weather_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        await do_weather(update, " ".join(context.args))
        return ConversationHandler.END
    await reply_anywhere(update, "Which city do you want the weather for?")
    return ASK_CITY


async def weather_city_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await do_weather(update, update.message.text.strip())
    return ConversationHandler.END


async def do_weather(update: Update, city: str):
    if not WEATHER_API_KEY:
        await reply_anywhere(update, "Weather isn't configured yet (set WEATHER_API_KEY).")
        return
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={WEATHER_API_KEY}&units=metric"
    )
    try:
        response = requests.get(url, timeout=5).json()
        if str(response.get("cod")) != "200":
            await reply_anywhere(update, "City not found.")
            return
        temp = response["main"]["temp"]
        desc = response["weather"][0]["description"]
        await reply_anywhere(update, f"{city.title()}: {temp}°C, {desc}")
    except Exception:
        await reply_anywhere(update, "Couldn't reach the weather service, try again shortly.")


# ---- Reminder conversation ----

async def remind_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_anywhere(update, "What should I remind you about?")
    return ASK_REMIND_TEXT


async def remind_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["remind_text"] = update.message.text.strip()
    await update.message.reply_text("In how many minutes should I remind you?")
    return ASK_REMIND_TIME


async def remind_time_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    if not raw.isdigit():
        await update.message.reply_text("Please send a number of minutes, e.g. 10")
        return ASK_REMIND_TIME

    minutes = int(raw)
    text = context.user_data.pop("remind_text", "Reminder!")
    chat_id = update.effective_chat.id

    if context.job_queue is None:
        await update.message.reply_text(
            'Reminder scheduling needs the job-queue extra: '
            'pip install "python-telegram-bot[job-queue]"'
        )
        return ConversationHandler.END

    context.job_queue.run_once(
        send_reminder,
        when=minutes * 60,
        chat_id=chat_id,
        data=text,
        name=f"remind_{chat_id}_{datetime.datetime.now().timestamp()}",
    )
    await update.message.reply_text(f"⏰ Got it — I'll remind you in {minutes} minute(s).")
    return ConversationHandler.END


async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(chat_id=job.chat_id, text=f"⏰ Reminder: {job.data}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ============================== MODERATION ==============================


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None):
    chat_id = update.effective_chat.id
    user_id = user_id or update.effective_user.id
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ("administrator", "creator")


async def admincheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message or update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer()
    if await is_admin(update, context):
        await target.reply_text("✅ You are an admin.")
    else:
        await target.reply_text("❌ You are not an admin.")


async def modhelp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "Reply to a user's message with /warn, /mute, /unmute or /kick.\n"
        "Destructive actions (/mute, /kick) ask you to confirm before doing anything."
    )


async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user's message with /warn to warn them.")
        return
    target = update.message.reply_to_message.from_user
    warnings[target.id] = warnings.get(target.id, 0) + 1
    await update.message.reply_text(
        f"⚠️ {target.first_name} has been warned. Total warnings: {warnings[target.id]}"
    )


async def view_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user's message with /warnings to check them.")
        return
    target = update.message.reply_to_message.from_user
    count = warnings.get(target.id, 0)
    await update.message.reply_text(f"{target.first_name} has {count} warning(s).")


async def clearwarnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user's message with /clearwarnings to clear them.")
        return
    target = update.message.reply_to_message.from_user
    warnings[target.id] = 0
    await update.message.reply_text(f"✅ Warnings cleared for {target.first_name}.")


async def request_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, verb: str):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text(f"Reply to a user's message with /{action} to {verb} them.")
        return
    target = update.message.reply_to_message.from_user
    pending_targets[target.id] = target.first_name
    await update.message.reply_text(
        f"{verb.capitalize()} {target.first_name}?",
        reply_markup=confirm_action(action, target.id),
    )


async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await request_confirmation(update, context, "mute", "mute")


async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user's message with /unmute to unmute them.")
        return
    target = update.message.reply_to_message.from_user
    await context.bot.restrict_chat_member(
        update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=True)
    )
    await update.message.reply_text(f"🔊 {target.first_name} has been unmuted.")


async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await request_confirmation(update, context, "kick", "remove")


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "confirm:cancel":
        await query.edit_message_text("Cancelled.")
        return

    _, action, user_id_str = data.split(":")
    user_id = int(user_id_str)
    chat_id = query.message.chat_id
    name = pending_targets.pop(user_id, "user")

    if not await is_admin(update, context, user_id=query.from_user.id):
        await query.edit_message_text("❌ Only admins can confirm this action.")
        return

    if action == "mute":
        await context.bot.restrict_chat_member(
            chat_id, user_id, permissions=ChatPermissions(can_send_messages=False)
        )
        await query.edit_message_text(f"🔇 {name} has been muted.")
    elif action == "kick":
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)
        await query.edit_message_text(f"👢 {name} has been removed from the group.")


# ============================== SOCIAL ==============================


async def share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.bot.username
    await reply_anywhere(update, f"Share me with your friends: https://t.me/{username}")


async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.bot.username
    await reply_anywhere(update, f"Invite link: https://t.me/{username}")


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else None
    if text:
        await update.message.reply_text("Thanks for your feedback! 🙏")
    else:
        await update.message.reply_text("Usage: /feedback your message here")


async def tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args) if context.args else None
    if name:
        await update.message.reply_text(f"📢 Hey @{name}, someone's calling you!")
    else:
        await update.message.reply_text("Usage: /tag username")


async def spotify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎵 Open Spotify", url="https://open.spotify.com/YOUR_LINK_HERE")]]
    )
    target = update.message or update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer()
    await target.reply_text("Here's the track:", reply_markup=keyboard)


async def youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Open YouTube", url="https://youtu.be/abc123xyz")]])
    target = update.message or update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer()
    await target.reply_text("Here's the video:", reply_markup=keyboard)


async def movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎬 Open Netflix", url="https://www.netflix.com")]])
    target = update.message or update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer()
    await target.reply_text("Watch here:", reply_markup=keyboard)


# ============================== WIRE IT ALL UP ==============================


def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # General
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CallbackQueryHandler(menu_router, pattern=r"^menu:"))

    # Fun / utility direct commands
    app.add_handler(CommandHandler("joke", joke))
    app.add_handler(CommandHandler("quote", quote))
    app.add_handler(CommandHandler("roll", roll))
    app.add_handler(CommandHandler("flip", flip))
    app.add_handler(CommandHandler("time", time_command))
    app.add_handler(CommandHandler("calc", calc))
    app.add_handler(CommandHandler("cat", cat))
    app.add_handler(CommandHandler("dog", dog))
    app.add_handler(CommandHandler("logo", logo))

    # Weather conversation
    weather_conv = ConversationHandler(
        entry_points=[
            CommandHandler("weather", weather_start),
            CallbackQueryHandler(weather_start, pattern=r"^act:weather$"),
        ],
        states={ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, weather_city_received)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(weather_conv)

    # Reminder conversation
    remind_conv = ConversationHandler(
        entry_points=[
            CommandHandler("remind", remind_start),
            CallbackQueryHandler(remind_start, pattern=r"^act:remind$"),
        ],
        states={
            ASK_REMIND_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, remind_text_received)],
            ASK_REMIND_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, remind_time_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(remind_conv)

    # Fun menu buttons
    app.add_handler(CallbackQueryHandler(joke, pattern=r"^act:joke$"))
    app.add_handler(CallbackQueryHandler(quote, pattern=r"^act:quote$"))
    app.add_handler(CallbackQueryHandler(roll, pattern=r"^act:roll$"))
    app.add_handler(CallbackQueryHandler(flip, pattern=r"^act:flip$"))
    app.add_handler(CallbackQueryHandler(time_command, pattern=r"^act:time$"))
    app.add_handler(CallbackQueryHandler(cat, pattern=r"^act:cat$"))
    app.add_handler(CallbackQueryHandler(dog, pattern=r"^act:dog$"))
    app.add_handler(CallbackQueryHandler(logo, pattern=r"^act:logo$"))

    # Moderation
    app.add_handler(CommandHandler("admincheck", admincheck))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("warnings", view_warnings))
    app.add_handler(CommandHandler("clearwarnings", clearwarnings))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CallbackQueryHandler(admincheck, pattern=r"^act:admincheck$"))
    app.add_handler(CallbackQueryHandler(modhelp, pattern=r"^act:modhelp$"))
    app.add_handler(CallbackQueryHandler(confirm_callback, pattern=r"^confirm:"))

    # Social
    app.add_handler(CommandHandler("share", share))
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CommandHandler("feedback", feedback))
    app.add_handler(CommandHandler("tag", tag))
    app.add_handler(CommandHandler("spotify", spotify))
    app.add_handler(CommandHandler("youtube", youtube))
    app.add_handler(CommandHandler("movie", movie))
    app.add_handler(CallbackQueryHandler(share, pattern=r"^act:share$"))
    app.add_handler(CallbackQueryHandler(invite, pattern=r"^act:invite$"))
    app.add_handler(CallbackQueryHandler(spotify, pattern=r"^act:spotify$"))
    app.add_handler(CallbackQueryHandler(youtube, pattern=r"^act:youtube$"))
    app.add_handler(CallbackQueryHandler(movie, pattern=r"^act:movie$"))

    # Fallback for plain text - added last so it never steals messages
    # that belong to an active conversation state.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

    return app


if __name__ == "__main__":
    if BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        raise RuntimeError("Edit this file and put your real bot token in BOT_TOKEN near the top.")
    application = build_app()
    print("Bot is running...")
    application.run_polling()

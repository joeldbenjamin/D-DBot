import os
import json
from pathlib import Path

import discord
from discord.ext import commands

# ─── CONFIG ───────────────────────────────────────────────────────────────────

# Load your bot token from the DISCORD_TOKEN environment variable
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")

# Configure intents so your bot can read message content
intents = discord.Intents.default()
intents.message_content = True

# Create the bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

# File to store state
DATA_FILE = Path("game_state.json")

# Weekday names
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ─── STATE LOADING ────────────────────────────────────────────────────────────

if DATA_FILE.exists():
    state = json.loads(DATA_FILE.read_text())
else:
    state = {"year": 1, "month": 1, "day": 1, "weekday": None}

state.setdefault("weekday", None)

def save_state():
    DATA_FILE.write_text(json.dumps(state, indent=2))

# ─── DATE ROLLOVER LOGIC ───────────────────────────────────────────────────────

def rollover_date(days: int):
    state["day"] += days
    # simple 30-day months, 12 months/year
    while state["day"] > 30:
        state["day"] -= 30
        state["month"] += 1
    while state["month"] > 12:
        state["month"] -= 12
        state["year"] += 1

    # update weekday if it's been set
    if state["weekday"] is not None:
        idx = WEEKDAYS.index(state["weekday"])
        idx = (idx + days) % 7
        state["weekday"] = WEEKDAYS[idx]

# ─── EVENTS & COMMANDS ────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command(name="date")
async def show_date(ctx, offset: str = None):
    """
    Show or adjust the in‑game date.
    • `!date` → shows current date
    • `!date +1` or `!date -2` → advances/rewinds by that many days, then shows new date
    """
    if offset:
        try:
            days = int(offset)    # int("+1")==1, int("-3")==-3
        except ValueError:
            return await ctx.send(
                "🚫 Invalid offset. Use `!date +N` or `!date -N`, e.g. `!date +1`"
            )
        rollover_date(days)
        save_state()
        y, m, d = state["year"], state["month"], state["day"]
        msg = f"🗓 Date adjusted by {days:+d} day(s). New date: Year {y}, Month {m}, Day {d}"
        if state["weekday"]:
            msg += f" ({state['weekday']})"
        return await ctx.send(msg)

    # no offset → just show the date
    y, m, d = state["year"], state["month"], state["day"]
    msg = f"📜 In‑game date: Year {y}, Month {m}, Day {d}"
    if state["weekday"]:
        msg += f" ({state['weekday']})"
    await ctx.send(msg)

@bot.command(name="setdate")
async def set_date(ctx, date_str: str):
    """Manually set the in‑game date: !setdate dd/mm/yyyy"""
    try:
        d_str, m_str, y_str = date_str.split("/")
        day, month, year = int(d_str), int(m_str), int(y_str)
        if not (1 <= month <= 12 and 1 <= day <= 31):
            raise ValueError
    except Exception:
        return await ctx.send("🚫 Invalid format. Use `!setdate dd/mm/yyyy`")

    state["day"], state["month"], state["year"] = day, month, year
    state["weekday"] = None
    save_state()
    await ctx.send(f"✅ Date set to Year {year}, Month {month}, Day {day}. Weekday cleared.")

@bot.command(name="advance", aliases=["addday"])
async def advance_date(ctx, days: int = 1):
    """Advance the in‑game date by N days (default 1): !advance [N] or !addday"""
    rollover_date(days)
    save_state()
    y, m, d = state["year"], state["month"], state["day"]
    msg = f"🗓 Advanced by {days} day(s). New date: Year {y}, Month {m}, Day {d}"
    if state["weekday"]:
        msg += f" ({state['weekday']})"
    await ctx.send(msg)

@bot.command(name="setweekday")
async def set_weekday(ctx, weekday: str):
    """Set the weekday for the current date: !setweekday Monday"""
    wd = weekday.capitalize()
    if wd not in WEEKDAYS:
        return await ctx.send("🚫 Invalid weekday. Choose from: " + ", ".join(WEEKDAYS))
    state["weekday"] = wd
    save_state()
    await ctx.send(f"✅ Weekday set to {wd}.")

# ─── RUN BOT ──────────────────────────────────────────────────────────────────

bot.run(TOKEN)

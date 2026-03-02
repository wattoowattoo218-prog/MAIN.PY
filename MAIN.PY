import discord
from discord.ext import commands
from discord import app_commands
import math
import json
import os
import random

# ================= TOKEN (SAFE) =================
TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= SETTINGS =================
BTC_RATE_PER_M = 0.00018
EXPRESS_MULTIPLIER = 1.15
DISCOUNT_ROLE_NAME = "VIP"
DISCOUNT_PERCENT = 10
TICKET_CATEGORY_NAME = "Orders"

# ================= DATA FILE =================
if not os.path.exists("orders.json"):
    with open("orders.json", "w") as f:
        json.dump({}, f)

def load_orders():
    with open("orders.json", "r") as f:
        return json.load(f)

def save_orders(data):
    with open("orders.json", "w") as f:
        json.dump(data, f, indent=4)

# ================= ALL SKILLS =================
skills = {
    "Attack": {"icon": "⚔️", "gp_per_xp": 120},
    "Strength": {"icon": "💪", "gp_per_xp": 120},
    "Defence": {"icon": "🛡️", "gp_per_xp": 120},
    "Hitpoints": {"icon": "❤️", "gp_per_xp": 100},
    "Ranged": {"icon": "🏹", "gp_per_xp": 130},
    "Prayer": {"icon": "🙏", "gp_per_xp": 300},
    "Magic": {"icon": "✨", "gp_per_xp": 150},
    "Cooking": {"icon": "🍳", "gp_per_xp": 80},
    "Woodcutting": {"icon": "🌲", "gp_per_xp": 90},
    "Fletching": {"icon": "🏹", "gp_per_xp": 110},
    "Fishing": {"icon": "🐟", "gp_per_xp": 95},
    "Firemaking": {"icon": "🔥", "gp_per_xp": 85},
    "Crafting": {"icon": "🧵", "gp_per_xp": 140},
    "Smithing": {"icon": "⚒️", "gp_per_xp": 160},
    "Mining": {"icon": "⛏️", "gp_per_xp": 170},
    "Herblore": {"icon": "🧪", "gp_per_xp": 250},
    "Agility": {"icon": "🤸", "gp_per_xp": 200},
    "Thieving": {"icon": "🕵️", "gp_per_xp": 180},
    "Slayer": {"icon": "🗡️", "gp_per_xp": 190},
    "Farming": {"icon": "🌾", "gp_per_xp": 220},
    "Runecrafting": {"icon": "🔮", "gp_per_xp": 300},
    "Hunter": {"icon": "🦅", "gp_per_xp": 160},
    "Construction": {"icon": "🏠", "gp_per_xp": 350},
    "Sailing": {"icon": "⚓", "gp_per_xp": 200}
}

# ================= XP FORMULA =================
def level_to_xp(level):
    xp = 0
    for i in range(1, level):
        xp += math.floor(i + 300 * 2 ** (i / 7.0))
    return math.floor(xp / 4)

# ================= PRICE CALC =================
def calculate_price(skill, start, stop, express, member):
    needed_xp = level_to_xp(stop) - level_to_xp(start)
    base_rate = skills[skill]["gp_per_xp"]

    rate = base_rate * (EXPRESS_MULTIPLIER if express else 1)
    total_gp = needed_xp * rate

    if any(role.name == DISCOUNT_ROLE_NAME for role in member.roles):
        total_gp -= total_gp * (DISCOUNT_PERCENT / 100)

    total_m = total_gp / 1_000_000
    total_btc = total_m * BTC_RATE_PER_M

    return needed_xp, rate, total_m, total_btc

# ================= SLASH CALC =================
@bot.tree.command(name="calc", description="Calculate service price")
async def calc(interaction: discord.Interaction,
               skill: str,
               start: int,
               stop: int,
               express: bool):

    if skill not in skills:
        return await interaction.response.send_message("Invalid skill.", ephemeral=True)

    if start >= stop:
        return await interaction.response.send_message("Stop must be higher than start.", ephemeral=True)

    xp, rate, total_m, btc = calculate_price(skill, start, stop, express, interaction.user)

    embed = discord.Embed(title=f"{skills[skill]['icon']} {skill} Quote", color=0x111111)
    embed.add_field(name="Levels", value=f"{start} ➜ {stop}", inline=False)
    embed.add_field(name="XP Needed", value=f"{xp:,}")
    embed.add_field(name="GP/XP", value=f"{rate:.2f}")
    embed.add_field(name="Total", value=f"{total_m:.2f}M")
    embed.add_field(name="BTC", value=f"{btc:.6f}")
    embed.add_field(name="Express", value="Yes" if express else "No")

    await interaction.response.send_message(embed=embed)

# ================= ORDER =================
@bot.tree.command(name="order", description="Create new order")
async def order(interaction: discord.Interaction,
                skill: str,
                start: int,
                stop: int,
                express: bool):

    if skill not in skills:
        return await interaction.response.send_message("Invalid skill.", ephemeral=True)

    if start >= stop:
        return await interaction.response.send_message("Stop must be higher than start.", ephemeral=True)

    xp, rate, total_m, btc = calculate_price(skill, start, stop, express, interaction.user)

    order_id = random.randint(1000, 9999)
    orders = load_orders()

    orders[str(order_id)] = {
        "user": interaction.user.id,
        "skill": skill,
        "start": start,
        "stop": stop,
        "total_m": total_m
    }

    save_orders(orders)

    category = discord.utils.get(interaction.guild.categories, name=TICKET_CATEGORY_NAME)
    if not category:
        category = await interaction.guild.create_category(TICKET_CATEGORY_NAME)

    channel = await interaction.guild.create_text_channel(
        name=f"order-{order_id}",
        category=category
    )

    embed = discord.Embed(title="🧾 New Order Created", color=discord.Color.green())
    embed.add_field(name="Order ID", value=order_id)
    embed.add_field(name="User", value=interaction.user.mention)
    embed.add_field(name="Skill", value=skill)
    embed.add_field(name="Levels", value=f"{start} ➜ {stop}")
    embed.add_field(name="Total", value=f"{total_m:.2f}M")

    await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ Order Created: {channel.mention}", ephemeral=True)

# ================= ADMIN RATE EDIT =================
@bot.tree.command(name="setrate", description="Admin: Set GP/XP rate")
@app_commands.checks.has_permissions(administrator=True)
async def setrate(interaction: discord.Interaction, skill: str, new_rate: int):
    if skill not in skills:
        return await interaction.response.send_message("Invalid skill.", ephemeral=True)

    skills[skill]["gp_per_xp"] = new_rate
    await interaction.response.send_message(f"Rate updated for {skill} → {new_rate} GP/XP")

# ================= READY =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"🔥 Boosting Bot Online: {bot.user}")

bot.run(TOKEN)

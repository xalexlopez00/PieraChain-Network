import discord
from discord import app_commands, Embed, ButtonStyle
from discord.ui import View, button
import asyncio
import random
import requests
import os
import pymongo
import urllib.parse
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
TOKEN = os.getenv("DISCORD_TOKEN")
API_BASE_URL = os.getenv("API_URL", "").strip("/")
MONGO_URI = os.getenv("MONGO_URI", "")

# --- LIMPIEZA DE URI ---
def get_clean_uri(uri):
    if not uri or "://" not in uri: return uri
    try:
        prefix, rest = uri.split("://", 1)
        creds, host = rest.rsplit("@", 1)
        if ":" in creds:
            u, p = creds.split(":", 1)
            return f"{prefix}://{urllib.parse.quote_plus(u)}:{urllib.parse.quote_plus(p)}@{host}"
    except: pass
    return uri

# Conexión con timeout para evitar bloqueos
client = pymongo.MongoClient(get_clean_uri(MONGO_URI), serverSelectionTimeoutMS=5000)
db_mongo = client["pieracoin_db"]
users_col = db_mongo["users"]

# --- FUNCIONES DB ---
def get_user(user_id):
    try: return users_col.find_one({"user_id": str(user_id)})
    except: return None

def update_user(user_id, address, last_login=None):
    data = {"address": address}
    if last_login: data["last_login"] = last_login
    try: users_col.update_one({"user_id": str(user_id)}, {"$set": data}, upsert=True)
    except: pass

# --- VISTA CON BOTONES ---
class PieraChainMenu(View):
    def __init__(self, address):
        super().__init__(timeout=None)
        self.address = address

    @discord.ui.button(label="⛏️ MINAR", style=ButtonStyle.success)
    async def mine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="⛏️ Minando bloque...", embed=None, view=None)
        await asyncio.sleep(random.randint(3, 5))
        try:
            r = requests.post(f"{API_BASE_URL}/mine?address={self.address}", timeout=15)
            if r.status_code == 200:
                data = r.json()
                new_bal = data.get('new_balance', '??')
                emb = Embed(title="✅ MINADO", description=f"Has recibido 50 PIERAS.\nNuevo Saldo: `{new_bal}`", color=0x2ECC71)
                await interaction.edit_original_response(content=None, embed=emb, view=self)
            else: raise Exception()
        except:
            await interaction.edit_original_response(content="❌ Error en el nodo.", view=self)

    @discord.ui.button(label="💰 SALDO", style=ButtonStyle.secondary)
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            r = requests.get(f"{API_BASE_URL}/balance/{self.address}", timeout=10).json()
            await interaction.response.send_message(f"🏦 Saldo: `{r['balance']} PIERAS`", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Error de conexión.", ephemeral=True)

# --- BOT SETUP ---
class PieraChainBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = PieraChainBot()

@bot.tree.command(name="id", description="Ver o crear wallet")
async def id_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True) # EVITA EL ERROR DE TIEMPO
    u_id = interaction.user.id
    u_data = get_user(u_id)
    
    if u_data:
        await interaction.followup.send(f"✅ Tu wallet: `{u_data['address']}`")
    else:
        try:
            r = requests.get(f"{API_BASE_URL}/wallet/generate", timeout=10).json()
            update_user(u_id, r["address"])
            emb = Embed(title="🧬 CREADA", description=f"Addr: `{r['address']}`\nKey: ||{r['private_key']}||", color=0x1ABC9C)
            await interaction.followup.send(embed=emb)
        except:
            await interaction.followup.send("❌ Error al generar wallet.")

@bot.tree.command(name="piera", description="Acceder al menú")
async def piera_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    u_data = get_user(interaction.user.id)
    if not u_data:
        return await interaction.followup.send("❌ Usa `/id` primero.")
    
    emb = Embed(title="🌌 TERMINAL", description=f"Wallet: `{u_data['address']}`", color=0x00FFCC)
    await interaction.followup.send(embed=emb, view=PieraChainMenu(u_data["address"]))

bot.run(TOKEN)

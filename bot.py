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

# --- LIMPIEZA DE URI (Seguridad extra) ---
def get_clean_uri(uri):
    if not uri or "://" not in uri: return uri
    try:
        protocol, rest = uri.split("://", 1)
        if "@" in rest:
            creds, host = rest.rsplit("@", 1)
            if ":" in creds:
                user, password = creds.split(":", 1)
                return f"{protocol}://{urllib.parse.quote_plus(user)}:{urllib.parse.quote_plus(password)}@{host}"
    except: pass
    return uri

# Intentamos conectar con un tiempo de espera corto para no congelar el bot
CLEAN_MONGO_URI = get_clean_uri(MONGO_URI)
client = pymongo.MongoClient(CLEAN_MONGO_URI, serverSelectionTimeoutMS=2000)
db_mongo = client["pieracoin_db"]
users_col = db_mongo["users"]

# --- FUNCIONES DE BASE DE DATOS CON TIMEOUT ---
def get_user(user_id):
    try:
        return users_col.find_one({"user_id": str(user_id)})
    except Exception as e:
        print(f"⚠️ Error DB (get_user): {e}")
        return None

def update_user(user_id, address):
    try:
        users_col.update_one(
            {"user_id": str(user_id)}, 
            {"$set": {"address": address, "last_active": datetime.now()}}, 
            upsert=True
        )
    except Exception as e:
        print(f"⚠️ Error DB (update_user): {e}")

# --- INTERFAZ DE MINERÍA ---
class PieraChainMenu(View):
    def __init__(self, address):
        super().__init__(timeout=None)
        self.address = address

    @discord.ui.button(label="⛏️ MINAR", style=ButtonStyle.success, custom_id="mine_btn")
    async def mine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="⚡ Minando...", embed=None, view=None)
        
        await asyncio.sleep(2) # Simulación breve
        
        try:
            r = requests.post(f"{API_BASE_URL}/mine?address={self.address}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                emb = Embed(title="✨ ¡ÉXITO!", description=f"Bloque minado.\nNuevo Saldo: `{data.get('new_balance')} PIERAS`", color=0x2ECC71)
                await interaction.edit_original_response(content=None, embed=emb, view=self)
            else:
                await interaction.edit_original_response(content="❌ El nodo rechazó la petición.", view=self)
        except Exception as e:
            await interaction.edit_original_response(content=f"⚠️ Error de red: `{e}`", view=self)

# --- BOT SETUP ---
class PieraChainBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = PieraChainBot()

@bot.tree.command(name="id", description="Crea o mira tu cuenta")
async def id_command(interaction: discord.Interaction):
    # CRITICAL: El defer evita el error de "La aplicación no respondió"
    await interaction.response.defer(ephemeral=True)
    
    u_id = interaction.user.id
    user_data = get_user(u_id)
    
    if user_data:
        await interaction.followup.send(f"✅ Tu wallet: `{user_data['address']}`")
    else:
        try:
            r = requests.get(f"{API_BASE_URL}/wallet/generate", timeout=10).json()
            update_user(u_id, r["address"])
            emb = Embed(title="🧬 WALLET GENERADA", description=f"**Dirección:** `{r['address']}`\n**Privada:** ||{r['private_key']}||", color=0x1ABC9C)
            await interaction.followup.send(embed=emb)
        except Exception as e:
            await interaction.followup.send(f"❌ Error al conectar con el nodo: `{e}`")

@bot.tree.command(name="piera", description="Panel de control")
async def piera_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    u_data = get_user(interaction.user.id)
    if not u_data:
        return await interaction.followup.send("❌ No tienes cuenta. Usa `/id`.")

    emb = Embed(title="🌌 TERMINAL", description=f"Wallet: `{u_data['address']}`", color=0x00FFCC)
    await interaction.followup.send(embed=emb, view=PieraChainMenu(u_data["address"]))

if __name__ == "__main__":
    bot.run(TOKEN)

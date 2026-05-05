import discord
from discord import app_commands, Embed, ButtonStyle
from discord.ui import View, button
import asyncio
import requests
import os
import pymongo
import urllib.parse
from datetime import datetime

# --- CONFIGURACIÓN ---
TOKEN = os.getenv("DISCORD_TOKEN")
API_BASE_URL = os.getenv("API_URL", "").strip("/")
MONGO_URI = os.getenv("MONGO_URI", "")

# --- LIMPIEZA DE URI PARA EVITAR ERRORES ---
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

# Conexión con tiempo de espera corto (2 segundos) para no bloquear el bot
client = pymongo.MongoClient(get_clean_uri(MONGO_URI), serverSelectionTimeoutMS=2000)
db_mongo = client["pieracoin_db"]
users_col = db_mongo["users"]

# --- FUNCIONES DE BASE DE DATOS ---
def get_user(user_id):
    try:
        return users_col.find_one({"user_id": str(user_id)})
    except: return None

def update_user(user_id, address):
    try:
        users_col.update_one({"user_id": str(user_id)}, {"$set": {"address": address}}, upsert=True)
    except: pass

# --- MENÚ DE BOTONES ---
class PieraChainMenu(View):
    def __init__(self, address):
        super().__init__(timeout=None)
        self.address = address

    @discord.ui.button(label="⛏️ MINAR", style=ButtonStyle.success, custom_id="mine_btn")
    async def mine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Avisamos que estamos trabajando
        await interaction.response.edit_message(content="⛏️ Procesando minería...", embed=None, view=None)
        
        try:
            # 2. Petición al nodo
            r = requests.post(f"{API_BASE_URL}/mine?address={self.address}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                emb = Embed(title="✨ BLOQUE MINADO", description=f"Nuevo Saldo: `{data.get('new_balance')} PIERAS`", color=0x2ECC71)
                await interaction.edit_original_response(content=None, embed=emb, view=self)
            else:
                await interaction.edit_original_response(content="❌ El nodo no respondió correctamente.", view=self)
        except Exception as e:
            await interaction.edit_original_response(content=f"⚠️ Error de conexión: `{e}`", view=self)

    @discord.ui.button(label="💰 SALDO", style=ButtonStyle.secondary, custom_id="bal_btn")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            r = requests.get(f"{API_BASE_URL}/balance/{self.address}", timeout=5).json()
            await interaction.response.send_message(f"🏦 Tu saldo actual es: `{r['balance']} PIERAS`", ephemeral=True)
        except:
            await interaction.response.send_message("❌ No se pudo conectar con la blockchain.", ephemeral=True)

# --- CONFIGURACIÓN DEL BOT ---
class PieraChainBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = PieraChainBot()

@bot.tree.command(name="id", description="Vincula tu cuenta o crea una nueva")
async def id_command(interaction: discord.Interaction):
    # CRITICO: Evita que Discord de error de "No respondió"
    await interaction.response.defer(ephemeral=True)
    
    user_data = get_user(interaction.user.id)
    if user_data:
        await interaction.followup.send(f"✅ Ya tienes una cuenta: `{user_data['address']}`")
    else:
        try:
            r = requests.get(f"{API_BASE_URL}/wallet/generate", timeout=10).json()
            update_user(interaction.user.id, r["address"])
            emb = Embed(title="🧬 WALLET CREADA", description=f"Dirección: `{r['address']}`\nPrivada: ||{r['private_key']}||", color=0x1ABC9C)
            await interaction.followup.send(embed=emb)
        except:
            await interaction.followup.send("❌ Error al conectar con el servidor de la blockchain.")

@bot.tree.command(name="piera", description="Abre el terminal de minería")
async def piera_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    u_data = get_user(interaction.user.id)
    if not u_data:
        return await interaction.followup.send("❌ Usa primero `/id` para crear tu cuenta.")

    emb = Embed(title="🌌 TERMINAL PIERACHAIN", description=f"Conectado como: `{u_data['address']}`", color=0x00FFCC)
    await interaction.followup.send(embed=emb, view=PieraChainMenu(u_data["address"]))

if __name__ == "__main__":
    bot.run(TOKEN)

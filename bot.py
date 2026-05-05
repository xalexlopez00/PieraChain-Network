import discord
from discord import app_commands, Embed, ButtonStyle
from discord.ui import View, button
import asyncio
import random
import requests
import os
import pymongo  # Librería para MongoDB
from datetime import datetime, timedelta

# --- CONFIGURACIÓN CON VARIABLES DE ENTORNO ---
TOKEN = os.getenv("DISCORD_TOKEN")
API_BASE_URL = os.getenv("API_URL", "http://0.0.0.0:10000")
MONGO_URI = os.getenv("MONGO_URI")

# --- CONEXIÓN A MONGODB ---
try:
    client = pymongo.MongoClient(MONGO_URI)
    db_mongo = client["pieracoin_db"]
    users_col = db_mongo["users"]
    print("✅ Conexión a MongoDB establecida con éxito.")
except Exception as e:
    print(f"❌ Error al conectar a MongoDB: {e}")

# --- FUNCIONES DE BASE DE DATOS ---
def get_user(user_id):
    """Busca un usuario en la nube"""
    return users_col.find_one({"user_id": str(user_id)})

def update_user(user_id, address, last_login=""):
    """Guarda o actualiza un usuario en la nube"""
    users_col.update_one(
        {"user_id": str(user_id)},
        {"$set": {"address": address, "last_login": last_login}},
        upsert=True
    )

# --- INTERFAZ DE MINERÍA ---
class PieraChainMenu(View):
    def __init__(self, address):
        super().__init__(timeout=None)
        self.address = address

    @discord.ui.button(label="⛏️ MINAR BLOQUE", style=ButtonStyle.success)
    async def mine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed_mining = Embed(
            title="🔨 Minería en curso...",
            description="Tu hardware está intentando resolver el hash.\n`Cargando algoritmos de PoW...`",
            color=0xF1C40F
        )
        await interaction.response.edit_message(embed=embed_mining, view=None)
        
        await asyncio.sleep(random.randint(4, 8)) 
        
        if random.random() < 0.25:
            try:
                r = requests.post(f"{API_BASE_URL}/mine?address={self.address}", timeout=10)
                if r.status_code == 200:
                    embed_win = Embed(
                        title="✅ ¡BLOQUE MINADO!",
                        description=f"Has encontrado un hash válido.\nRecibes: **50.00 PIERAS** 🪙",
                        color=0x2ECC71
                    )
                    await interaction.edit_original_response(embed=embed_win, view=self)
                else:
                    raise Exception("Error en API")
            except Exception as e:
                await interaction.edit_original_response(content=f"❌ Error de nodo: {str(e)}", embed=None, view=self)
        else:
            embed_fail = Embed(
                title="❌ HASH NO VÁLIDO",
                description="Potencia insuficiente. ¡Inténtalo de nuevo!",
                color=0xE74C3C
            )
            await interaction.edit_original_response(embed=embed_fail, view=self)

    @discord.ui.button(label="💰 SALDO", style=ButtonStyle.secondary)
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            r = requests.get(f"{API_BASE_URL}/balance/{self.address}", timeout=10)
            data = r.json()
            embed_bal = Embed(
                title="💎 Tu Cartera",
                description=f"Dirección: `{self.address}`\nSaldo: **{data['balance']} PIERAS**",
                color=0x3498DB
            )
            await interaction.response.send_message(embed=embed_bal, ephemeral=True)
        except:
            await interaction.response.send_message("❌ Error al conectar con la blockchain.", ephemeral=True)

# --- CLASE DEL BOT ---
class PieraChainBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Comandos sincronizados para {self.user}")

bot = PieraChainBot()

@bot.tree.command(name="id", description="Gestión de identidad PieraChain")
async def id(interaction: discord.Interaction):
    u_id = str(interaction.user.id)
    user_data = get_user(u_id)
    
    if user_data:
        addr = user_data["address"]
        embed = Embed(title="🔐 Tu Cuenta Activa", color=0x9B59B6)
        embed.description = f"Registrada en la nube:\n\n`{addr}`"
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        try:
            r = requests.get(f"{API_BASE_URL}/wallet/generate", timeout=10)
            r_data = r.json()
            update_user(u_id, r_data["address"])
            
            embed = Embed(title="🧬 Identidad Creada", color=0x1ABC9C)
            embed.add_field(name="Wallet Address", value=f"`{r_data['address']}`", inline=False)
            embed.add_field(name="Private Key", value=f"||{r_data['private_key']}||", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="piera", description="Acceder al terminal de minería")
async def piera(interaction: discord.Interaction, direccion: str = None):
    u_id = str(interaction.user.id)
    user_data = get_user(u_id)
    ahora = datetime.now()

    if not user_data:
        await interaction.response.send_message("❌ No tienes cuenta. Usa `/id`.", ephemeral=True)
        return

    es_valido = False
    
    if user_data.get("last_login"):
        try:
            last_login = datetime.fromisoformat(user_data["last_login"])
            if ahora - last_login < timedelta(days=1):
                es_valido = True
        except: pass

    if direccion and direccion == user_data["address"]:
        update_user(u_id, user_data["address"], ahora.isoformat())
        es_valido = True

    if es_valido:
        embed = Embed(title="🎮 PieraChain Terminal", description="Conectado a la red.", color=0x00FFCC)
        await interaction.response.send_message(embed=embed, view=PieraChainMenu(user_data["address"]), ephemeral=True)
    else:
        await interaction.response.send_message("🔒 **Sesión Expirada.**\nUsa `/piera direccion:TU_ADDRESS` para entrar.", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)

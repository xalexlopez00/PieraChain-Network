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
API_BASE_URL = os.getenv("API_URL")
MONGO_URI = os.getenv("MONGO_URI", "")

# --- FUNCIÓN DE LIMPIEZA DE URI ---
def get_clean_uri(uri):
    if not uri: return uri
    try:
        if "://" in uri and "@" in uri:
            protocol, rest = uri.split("://", 1)
            creds, host = rest.rsplit("@", 1)
            if ":" in creds:
                user, password = creds.split(":", 1)
                return f"{protocol}://{urllib.parse.quote_plus(user)}:{urllib.parse.quote_plus(password)}@{host}"
    except: pass
    return uri

CLEAN_MONGO_URI = get_clean_uri(MONGO_URI)

# --- CONEXIÓN A MONGODB ---
try:
    client = pymongo.MongoClient(CLEAN_MONGO_URI, serverSelectionTimeoutMS=5000)
    db_mongo = client["pieracoin_db"]
    users_col = db_mongo["users"]
    client.server_info()
    print("✅ [DATABASE] Conexión establecida con MongoDB Atlas.")
except Exception as e:
    print(f"❌ [DATABASE] Error crítico: {e}")

# --- FUNCIONES AUXILIARES ---
def get_user(user_id):
    try:
        return users_col.find_one({"user_id": str(user_id)})
    except:
        return None

def update_user(user_id, address, last_login=None):
    data = {"address": address}
    if last_login:
        data["last_login"] = last_login
    users_col.update_one({"user_id": str(user_id)}, {"$set": data}, upsert=True)

# --- INTERFAZ VISUAL ---
class PieraChainMenu(View):
    def __init__(self, address):
        super().__init__(timeout=None)
        self.address = address

    @discord.ui.button(label="⛏️ INICIAR MINADO", style=ButtonStyle.success, custom_id="mine_btn")
    async def mine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # CORREGIDO: Eliminado el salto de línea que rompía el string
        embed_mining = Embed(
            title="⚡ CONECTANDO AL NODO...",
            description="```fix\nStatus: Ejecutando algoritmos PoW\nHashrate: 45.2 MH/s```\nBuscando un nonce válido...",
            color=0xF1C40F
        )
        await interaction.response.edit_message(embed=embed_mining, view=None)
        
        # Simulación de trabajo de minería
        await asyncio.sleep(random.randint(4, 7)) 
        
        if random.random() < 0.25:
            try:
                r = requests.post(f"{API_BASE_URL}/mine?address={self.address}", timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    new_bal = data.get('new_balance', '??')
                    embed_win = Embed(
                        title="✨ ¡BLOQUE MINADO!",
                        description=f"### 🎊 ¡Felicidades!\n> **Recompensa:** `+50.00 PIERAS` 🪙\n> **Nuevo Saldo:** `{new_bal} PIERAS`",
                        color=0x2ECC71
                    )
                    await interaction.edit_original_response(embed=embed_win, view=self)
                else: 
                    raise Exception("Error en la respuesta del nodo")
            except Exception as e:
                await interaction.edit_original_response(content=f"⚠️ Error de conexión: `{e}`", embed=None, view=self)
        else:
            embed_fail = Embed(
                title="❌ HASH RECHAZADO", 
                description="Tu hardware no encontró una solución válida esta vez. ¡Reintenta!", 
                color=0xE74C3C
            )
            await interaction.edit_original_response(embed=embed_fail, view=self)

    @discord.ui.button(label="💰 CARTERA", style=ButtonStyle.secondary, custom_id="bal_btn")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            r = requests.get(f"{API_BASE_URL}/balance/{self.address}", timeout=10)
            data = r.json()
            embed_bal = Embed(
                title="🏦 ESTADO DE CUENTA", 
                description=f"**Dirección:** `{self.address}`\n## {data['balance']} PIERAS 🪙", 
                color=0x3498DB
            )
            await interaction.response.send_message(embed=embed_bal, ephemeral=True)
        except:
            await interaction.response.send_message("❌ Error: No se pudo obtener el saldo del nodo.", ephemeral=True)

# --- BOT ---
class PieraChainBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"🚀 Slash commands sincronizados.")
        print(f"🚀 Bot listo: {self.user}")

bot = PieraChainBot()

@bot.tree.command(name="id", description="Ver o crear tu wallet")
async def id_command(interaction: discord.Interaction):
    user_data = get_user(interaction.user.id)
    if user_data:
        await interaction.response.send_message(f"✅ Tu wallet ya está vinculada: `{user_data['address']}`", ephemeral=True)
    else:
        await interaction.response.defer(ephemeral=True)
        try:
            # Llamada a la API para generar llaves
            r = requests.get(f"{API_BASE_URL}/wallet/generate", timeout=10).json()
            update_user(interaction.user.id, r["address"])
            
            embed = Embed(
                title="🧬 WALLET GENERADA", 
                description=f"**Dirección Pública:** `{r['address']}`\n**Llave Privada:** || {r['private_key']} ||\n\n*Guarda tu llave privada, es secreta.*", 
                color=0x1ABC9C
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error al generar wallet: `{e}`", ephemeral=True)

@bot.tree.command(name="piera", description="Panel de minería")
async def piera_command(interaction: discord.Interaction, direccion: str = None):
    u_data = get_user(interaction.user.id)
    if not u_data: 
        return await interaction.response.send_message("❌ No tienes una cuenta. Usa `/id` primero.", ephemeral=True)
    
    addr = u_data["address"]
    # Si el usuario provee una dirección, verificamos que sea la suya
    if direccion and direccion != addr:
        return await interaction.response.send_message("❌ La dirección proporcionada no coincide con tu registro.", ephemeral=True)

    embed = Embed(
        title="🌌 TERMINAL PIERACHAIN", 
        description=f"Bienvenido, **{interaction.user.name}**\nNodo: `🟢 Conectado`", 
        color=0x00FFCC
    )
    await interaction.response.send_message(embed=embed, view=PieraChainMenu(addr), ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: No se encontró el DISCORD_TOKEN en las variables de entorno.")
    else:
        bot.run(TOKEN)

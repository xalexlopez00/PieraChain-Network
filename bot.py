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

# --- CONFIGURACIÓN CON VARIABLES DE ENTORNO ---
TOKEN = os.getenv("DISCORD_TOKEN")
API_BASE_URL = os.getenv("API_URL", "http://0.0.0.0:10000")
MONGO_URI = os.getenv("MONGO_URI")

# --- LIMPIEZA DE URI (Para evitar error InvalidURI si hay caracteres especiales) ---
if MONGO_URI and "@" in MONGO_URI:
    try:
        prefix, rest = MONGO_URI.split("://", 1)
        user_pass, host = rest.split("@", 1)
        if ":" in user_pass:
            user, password = user_pass.split(":", 1)
            user = urllib.parse.quote_plus(user)
            password = urllib.parse.quote_plus(password)
            MONGO_URI = f"{prefix}://{user}:{password}@{host}"
    except:
        pass

# --- CONEXIÓN A MONGODB ---
try:
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db_mongo = client["pieracoin_db"]
    users_col = db_mongo["users"]
    client.server_info()
    print("✅ [DATABASE] Conexión establecida con MongoDB Atlas.")
except Exception as e:
    print(f"❌ [DATABASE] Error crítico de conexión: {e}")

# --- FUNCIONES DE BASE DE DATOS ---
def get_user(user_id):
    return users_col.find_one({"user_id": str(user_id)})

def update_user(user_id, address, last_login=None):
    data = {"address": address}
    if last_login:
        data["last_login"] = last_login
    users_col.update_one({"user_id": str(user_id)}, {"$set": data}, upsert=True)

# --- INTERFAZ VISUAL: MENÚ DE MINERÍA ---
class PieraChainMenu(View):
    def __init__(self, address):
        super().__init__(timeout=None)
        self.address = address

    @discord.ui.button(label="⛏️ INICIAR MINADO", style=ButtonStyle.success, custom_id="mine_btn")
    async def mine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed_mining = Embed(
            title="⚡ CONECTANDO AL NODO...",
            description=(
                "```fix\n"
                "Status: Ejecutando algoritmos PoW\n"
                "Hashrate: 45.2 MH/s\n"
                "Dificultad: Dinámica\n"
                "```\n"
                "Buscando un nonce válido en la red..."
            ),
            color=0xF1C40F
        )
        await interaction.response.edit_message(embed=embed_mining, view=None)
        
        await asyncio.sleep(random.randint(4, 7)) 
        
        if random.random() < 0.25: # 25% de probabilidad de éxito
            try:
                r = requests.post(f"{API_BASE_URL}/mine?address={self.address}", timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    new_bal = data.get('new_balance', '??')
                    
                    embed_win = Embed(
                        title="✨ ¡BLOQUE MINADO CON ÉXITO!",
                        description=(
                            f"### 🎊 ¡Felicidades, minero!\n"
                            f"Has resuelto el acertijo criptográfico.\n\n"
                            f"> **Recompensa:** `+50.00 PIERAS` 🪙\n"
                            f"> **Nuevo Saldo:** `{new_bal} PIERAS`"
                        ),
                        color=0x2ECC71
                    )
                    embed_win.set_footer(text=f"TXID: {random.getrandbits(64)}")
                    await interaction.edit_original_response(embed=embed_win, view=self)
                else:
                    raise Exception("Fallo en la validación del nodo")
            except Exception as e:
                await interaction.edit_original_response(content=f"⚠️ **Error de red:** `{e}`", embed=None, view=self)
        else:
            embed_fail = Embed(
                title="❌ HASH RECHAZADO",
                description="Tu hardware no ha encontrado una solución válida. ¡Reintenta!",
                color=0xE74C3C
            )
            await interaction.edit_original_response(embed=embed_fail, view=self)

    @discord.ui.button(label="💰 VER CARTERA", style=ButtonStyle.secondary, custom_id="bal_btn")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            r = requests.get(f"{API_BASE_URL}/balance/{self.address}", timeout=10)
            data = r.json()
            embed_bal = Embed(
                title="🏦 ESTADO DE CUENTA",
                description=(
                    f"**Dirección:** `{self.address}`\n\n"
                    f"**Saldo Disponible:**\n## {data['balance']} PIERAS 🪙"
                ),
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
        print(f"🚀 [SISTEMA] Bot {self.user} sincronizado.")

bot = PieraChainBot()

@bot.tree.command(name="id", description="Ver o crear tu identidad criptográfica")
async def id_command(interaction: discord.Interaction):
    u_id = str(interaction.user.id)
    user_data = get_user(u_id)
    
    if user_data:
        addr = user_data["address"]
        embed = Embed(
            title="🔐 IDENTIDAD DETECTADA",
            description=f"Cuenta vinculada:\n\n`{addr}`",
            color=0x9B59B6
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.defer(ephemeral=True)
        try:
            r = requests.get(f"{API_BASE_URL}/wallet/generate", timeout=10)
            r_data = r.json()
            update_user(u_id, r_data["address"])
            
            embed = Embed(
                title="🧬 NUEVA IDENTIDAD GENERADA",
                description=(
                    f"**Dirección Pública:**\n`{r_data['address']}`\n\n"
                    f"**Llave Privada:**\n|| {r_data['private_key']} ||"
                ),
                color=0x1ABC9C
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)

@bot.tree.command(name="piera", description="Abrir el Terminal de Minería")
async def piera_command(interaction: discord.Interaction, direccion: str = None):
    u_id = str(interaction.user.id)
    user_data = get_user(u_id)
    ahora = datetime.now()

    if not user_data:
        return await interaction.response.send_message("❌ Usa `/id` primero.", ephemeral=True)

    addr_reg = user_data["address"]
    es_valido = False
    
    if user_data.get("last_login"):
        try:
            last_login = datetime.fromisoformat(user_data["last_login"])
            if ahora - last_login < timedelta(days=1):
                es_valido = True
        except: pass

    if direccion and direccion == addr_reg:
        update_user(u_id, addr_reg, ahora.isoformat())
        es_valido = True

    if es_valido:
        embed = Embed(
            title="🌌 TERMINAL PIERACHAIN",
            description=f"Usuario: **{interaction.user.name}**\nNodo: `🟢 Online`",
            color=0x00FFCC
        )
        await interaction.response.send_message(embed=embed, view=PieraChainMenu(addr_reg), ephemeral=True)
    else:
        await interaction.response.send_message("🔒 Sesión expirada. Usa `/piera direccion:TU_ADDRESS`.", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)

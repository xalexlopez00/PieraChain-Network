import discord
from discord import app_commands, Embed, ButtonStyle
from discord.ui import View, button
import asyncio
import random
import requests
import json
import os
from datetime import datetime, timedelta

# --- CONFIGURACIÓN CON VARIABLES DE ENTORNO ---
# En Render, configura DISCORD_TOKEN y API_URL en la pestaña 'Environment'
TOKEN = os.getenv("DISCORD_TOKEN")
API_BASE_URL = os.getenv("API_URL", "http://0.0.0.0:10000")
DB_FILE = "users_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: 
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return {}
    return {}

def save_db(db):
    with open(DB_FILE, "w") as f: 
        json.dump(db, f, indent=4)

# --- INTERFAZ DE MINERÍA PREMIUM ---
class PieraChainMenu(View):
    def __init__(self, address):
        super().__init__(timeout=None)
        self.address = address

    @discord.ui.button(label="⛏️ MINAR BLOQUE", style=ButtonStyle.success)
    async def mine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed_mining = Embed(
            title="🔨 Minería en curso...",
            description="Tu hardware está intentando resolver el hash del bloque actual.\n`Cargando algoritmos de Proof of Work...`",
            color=0xF1C40F
        )
        await interaction.response.edit_message(embed=embed_mining, view=None)
        
        await asyncio.sleep(random.randint(4, 8)) 
        
        if random.random() < 0.25:
            try:
                # Petición a la API interna
                r = requests.post(f"{API_BASE_URL}/mine?address={self.address}", timeout=10)
                if r.status_code == 200:
                    embed_win = Embed(
                        title="✅ ¡BLOQUE MINADO!",
                        description=f"¡Felicidades! Has encontrado un hash válido.\nRecibes: **50.00 PIERAS** 🪙",
                        color=0x2ECC71
                    )
                    embed_win.set_footer(text="La transacción ha sido grabada en la blockchain.")
                    await interaction.edit_original_response(embed=embed_win, view=self)
                else:
                    raise Exception("Status error")
            except Exception as e:
                await interaction.edit_original_response(content=f"❌ Error de conexión con el nodo: {str(e)}", embed=None, view=self)
        else:
            embed_fail = Embed(
                title="❌ HASH NO VÁLIDO",
                description="La potencia de minado no ha sido suficiente para este bloque.\n¡Vuelve a intentarlo!",
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
                description=f"Dirección vinculada:\n`{self.address}`\n\nSaldo disponible:\n**{data['balance']} PIERAS**",
                color=0x3498DB
            )
            await interaction.response.send_message(embed=embed_bal, ephemeral=True)
        except:
            await interaction.response.send_message("❌ No se pudo conectar con el banco central.", ephemeral=True)

# --- CLASE DEL BOT ---
class PieraChainBot(discord.Client):
    def __init__(self):
        # Aseguramos los intents necesarios
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Comandos sincronizados para {self.user}")

bot = PieraChainBot()

@bot.tree.command(name="id", description="Gestión de identidad PieraChain")
async def id(interaction: discord.Interaction):
    db = load_db()
    u_id = str(interaction.user.id)
    
    if u_id in db:
        addr = db[u_id]["address"]
        embed = Embed(title="🔐 Tu Cuenta Activa", color=0x9B59B6)
        embed.description = f"Ya tienes una identidad registrada en la red:\n\n`{addr}`"
        embed.set_footer(text="Usa /piera para acceder a tu terminal.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        try:
            r = requests.get(f"{API_BASE_URL}/wallet/generate", timeout=10)
            r_data = r.json()
            db[u_id] = {"address": r_data["address"], "last_login": ""}
            save_db(db)
            
            embed = Embed(title="🧬 Identidad Creada", color=0x1ABC9C)
            embed.add_field(name="Wallet Address", value=f"`{r_data['address']}`", inline=False)
            embed.add_field(name="Private Key (NO COMPARTIR)", value=f"||{r_data['private_key']}||", inline=False)
            embed.set_footer(text="Información privada. Solo tú puedes ver este mensaje.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al generar wallet: {str(e)}", ephemeral=True)

@bot.tree.command(name="piera", description="Acceder al terminal de minería")
async def piera(interaction: discord.Interaction, direccion: str = None):
    db = load_db()
    u_id = str(interaction.user.id)
    ahora = datetime.now()

    if u_id not in db:
        await interaction.response.send_message("❌ No tienes cuenta. Usa `/id` primero.", ephemeral=True)
        return

    data = db[u_id]
    es_valido = False
    
    # Comprobar si la última sesión fue hace menos de 24h
    if data.get("last_login"):
        try:
            last_login = datetime.fromisoformat(data["last_login"])
            if ahora - last_login < timedelta(days=1):
                es_valido = True
        except ValueError:
            pass

    # Si introduce la dirección manualmente, validamos y renovamos sesión
    if direccion:
        if direccion == data["address"]:
            data["last_login"] = ahora.isoformat()
            save_db(db)
            es_valido = True
        else:
            await interaction.response.send_message("❌ La dirección no coincide con tu registro.", ephemeral=True)
            return

    if es_valido:
        embed = Embed(title="🎮 PieraChain Terminal", description="Sistema de minería conectado.", color=0x00FFCC)
        embed.add_field(name="Nodo", value="`Render-Cloud-v1`", inline=True)
        embed.add_field(name="Estado", value="`🟢 Online`", inline=True)
        await interaction.response.send_message(embed=embed, view=PieraChainMenu(data["address"]), ephemeral=True)
    else:
        await interaction.response.send_message("🔒 **Sesión Expirada.**\nIntroduce tu dirección para verificar tu identidad hoy:\n`/piera direccion:TU_DIRECCION`", ephemeral=True)

# Ejecución segura
if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Error: No hay DISCORD_TOKEN. Configúralo en las variables de entorno de Render.")
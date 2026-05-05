import discord
from discord import app_commands, Embed, ButtonStyle
from discord.ui import View, button
import asyncio
import requests
import os

# --- CONFIGURACIÓN ---
TOKEN = os.getenv("DISCORD_TOKEN")
API_BASE_URL = os.getenv("API_URL", "").strip("/")
DB_FILE = "database.txt"

# --- FUNCIONES DE "BASE DE DATOS" TXT ---
def get_user_address(user_id):
    """Busca la dirección de un usuario en el archivo TXT"""
    if not os.path.exists(DB_FILE):
        return None
    with open(DB_FILE, "r") as f:
        for line in f:
            # Formato esperado: user_id:address
            if ":" in line:
                uid, addr = line.strip().split(":", 1)
                if uid == str(user_id):
                    return addr
    return None

def save_user(user_id, address):
    """Guarda un nuevo usuario en el archivo TXT"""
    with open(DB_FILE, "a") as f:
        f.write(f"{user_id}:{address}\n")

# --- INTERFAZ CON BOTONES ---
class PieraChainMenu(View):
    def __init__(self, address):
        super().__init__(timeout=None)
        self.address = address

    @discord.ui.button(label="⛏️ MINAR", style=ButtonStyle.success, custom_id="mine_btn")
    async def mine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="⛏️ Minando bloque... espera.", embed=None, view=None)
        
        try:
            # Petición a la API del nodo
            r = requests.post(f"{API_BASE_URL}/mine?address={self.address}", timeout=15)
            if r.status_code == 200:
                data = r.json()
                new_bal = data.get('new_balance', '??')
                emb = Embed(title="✨ ¡MINADO CON ÉXITO!", description=f"Has recibido tu recompensa.\n\n**Saldo Actual:** `{new_bal} PIERAS` 🪙", color=0x2ECC71)
                await interaction.edit_original_response(content=None, embed=emb, view=self)
            else:
                await interaction.edit_original_response(content="❌ El nodo está ocupado o dio error.", view=self)
        except Exception as e:
            await interaction.edit_original_response(content=f"⚠️ Error de conexión con el nodo: `{e}`", view=self)

    @discord.ui.button(label="💰 SALDO", style=ButtonStyle.secondary, custom_id="bal_btn")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            r = requests.get(f"{API_BASE_URL}/balance/{self.address}", timeout=10).json()
            await interaction.response.send_message(f"🏦 Tu saldo es: **{r['balance']} PIERAS**", ephemeral=True)
        except:
            await interaction.response.send_message("❌ No pude consultar el saldo.", ephemeral=True)

# --- BOT SETUP ---
class PieraChainBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Bot conectado como {self.user}")

bot = PieraChainBot()

@bot.tree.command(name="id", description="Ver o crear tu wallet")
async def id_command(interaction: discord.Interaction):
    # Esto evita el error de "La aplicación no respondió"
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    address = get_user_address(user_id)
    
    if address:
        await interaction.followup.send(f"✅ Tu wallet vinculada es: `{address}`")
    else:
        try:
            # Generamos wallet en el nodo
            r = requests.get(f"{API_BASE_URL}/wallet/generate", timeout=10).json()
            new_addr = r["address"]
            save_user(user_id, new_addr)
            
            emb = Embed(title="🧬 WALLET GENERADA", description=f"**Dirección:** `{new_addr}`\n**Llave Privada:** ||{r['private_key']}||", color=0x1ABC9C)
            await interaction.followup.send(embed=emb)
        except Exception as e:
            await interaction.followup.send(f"❌ Error al crear wallet: `{e}`")

@bot.tree.command(name="piera", description="Abrir menú de minería")
async def piera_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    address = get_user_address(interaction.user.id)
    if not address:
        return await interaction.followup.send("❌ No tienes cuenta. Usa `/id` primero.")

    emb = Embed(title="🌌 TERMINAL PIERACHAIN", description=f"Bienvenido. Wallet activa:\n`{address}`", color=0x00FFCC)
    await interaction.followup.send(embed=emb, view=PieraChainMenu(address))

bot.run(TOKEN)

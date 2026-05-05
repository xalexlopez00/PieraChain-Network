from fastapi import FastAPI
import pymongo
import os
import urllib.parse # <--- Añadido para procesar la URL
from core.blockchain import Blockchain
from core.wallet import Wallet

app = FastAPI(title="PieraChain API", description="Nodo Blockchain para Render")

# --- CONEXIÓN A MONGODB CON LIMPIEZA DE URI ---
MONGO_URI = os.getenv("MONGO_URI")

# Esta lógica separa la contraseña, la limpia y vuelve a montar la URL
if MONGO_URI and "@" in MONGO_URI:
    prefix, rest = MONGO_URI.split("://", 1)
    user_pass, host = rest.split("@", 1)
    if ":" in user_pass:
        user, password = user_pass.split(":", 1)
        # Codifica caracteres especiales en el usuario y password
        user = urllib.parse.quote_plus(user)
        password = urllib.parse.quote_plus(password)
        MONGO_URI = f"{prefix}://{user}:{password}@{host}"

client = pymongo.MongoClient(MONGO_URI)
db_mongo = client["pieracoin_db"]
balances_col = db_mongo["balances"]

pierachain = Blockchain()

@app.get("/")
def home():
    return {"message": "PieraChain Node is Online", "docs": "/docs"}

@app.get("/status")
def status(): 
    return {
        "height": len(pierachain.chain), 
        "last_block": pierachain.chain[-1]
    }

@app.get("/balance/{address}")
def balance(address: str): 
    user_data = balances_col.find_one({"address": address})
    if user_data:
        return {"balance": user_data["balance"]}
    return {"balance": pierachain.get_balance(address)}

@app.post("/mine")
def mine(address: str): 
    block = pierachain.mine_block(address)
    user_data = balances_col.find_one({"address": address})
    current_balance = user_data["balance"] if user_data else 0.0
    new_balance = current_balance + 50.0
    
    balances_col.update_one(
        {"address": address},
        {"$set": {"balance": new_balance}},
        upsert=True
    )
    block["new_balance"] = new_balance
    return block

@app.get("/wallet/generate")
def generate_wallet():
    return Wallet.generate_keys()

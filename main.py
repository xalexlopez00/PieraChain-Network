from fastapi import FastAPI
import pymongo
import os
import urllib.parse
from core.blockchain import Blockchain
from core.wallet import Wallet

app = FastAPI(title="PieraChain API", description="Nodo Blockchain para Render")

# --- LÓGICA DE CONEXIÓN ROBUSTA ---
MONGO_URI = os.getenv("MONGO_URI", "")

def get_clean_uri(uri):
    if not uri:
        return uri
    try:
        # Si la URI ya está codificada o es local, no hacemos nada complejo
        if "mongodb+srv://" not in uri and "mongodb://" not in uri:
            return uri
        
        # Separamos el protocolo (mongodb+srv://) del resto
        protocol, rest = uri.split("://", 1)
        # Separamos credenciales del host
        if "@" in rest:
            creds, host = rest.rsplit("@", 1)
            # Separamos usuario de contraseña
            if ":" in creds:
                user, password = creds.split(":", 1)
                user = urllib.parse.quote_plus(user)
                password = urllib.parse.quote_plus(password)
                return f"{protocol}://{user}:{password}@{host}"
    except Exception:
        pass
    return uri

# Aplicamos la limpieza
CLEAN_MONGO_URI = get_clean_uri(MONGO_URI)
client = pymongo.MongoClient(CLEAN_MONGO_URI)
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

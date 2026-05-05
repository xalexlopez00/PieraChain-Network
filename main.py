from fastapi import FastAPI
import pymongo
import os
from core.blockchain import Blockchain
from core.wallet import Wallet

app = FastAPI(title="PieraChain API", description="Nodo Blockchain para Render")

# --- CONEXIÓN A MONGODB ---
MONGO_URI = os.getenv("MONGO_URI")
client = pymongo.MongoClient(MONGO_URI)
db_mongo = client["pieracoin_db"]
balances_col = db_mongo["balances"] # Colección para guardar monedas

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
    # Primero intentamos buscar el saldo en MongoDB
    user_data = balances_col.find_one({"address": address})
    if user_balance := user_data:
        return {"balance": user_balance["balance"]}
    
    # Si no existe en Mongo, consultamos la blockchain local (por si acaso)
    return {"balance": pierachain.get_balance(address)}

@app.post("/mine")
def mine(address: str): 
    # 1. Ejecutamos el minado técnico
    block = pierachain.mine_block(address)
    
    # 2. ACTUALIZACIÓN PERSISTENTE: Guardamos el premio en MongoDB
    # Buscamos cuánto tiene ahora mismo
    user_data = balances_col.find_one({"address": address})
    current_balance = user_data["balance"] if user_data else 0.0
    
    # Sumamos la recompensa (ejemplo: 50 PIERAS)
    new_balance = current_balance + 50.0
    
    # Guardamos el nuevo total en la nube
    balances_col.update_one(
        {"address": address},
        {"$set": {"balance": new_balance}},
        upsert=True
    )
    
    # Devolvemos el bloque y el saldo actualizado para que el bot lo vea
    block["new_balance"] = new_balance
    return block

@app.get("/wallet/generate")
def generate_wallet():
    return Wallet.generate_keys()

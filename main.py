from fastapi import FastAPI
from core.blockchain import Blockchain
from core.wallet import Wallet

app = FastAPI(title="PieraChain API", description="Nodo Blockchain para Render")
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
    return {"balance": pierachain.get_balance(address)}

@app.post("/mine")
def mine(address: str): 
    # El proceso de minado ahora devuelve el bloque completo
    return pierachain.mine_block(address)

@app.get("/wallet/generate")
def generate_wallet():
    # Esta es la ruta que te daba 404 antes
    return Wallet.generate_keys()
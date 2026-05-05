import os
import json
import hashlib
from ecdsa import SigningKey, SECP256k1


WALLET_FILE = "wallet.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def create_wallet():
    if os.path.exists(WALLET_FILE):
        print("[INFO] Ya existe una cartera:", WALLET_FILE)
        return

    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.get_verifying_key()

    private_key_hex = sk.to_string().hex()
    public_key_hex = vk.to_string().hex()

    # Dirección = hash de la clave pública
    address = sha256(bytes.fromhex(public_key_hex))[:40]

    wallet_data = {
        "private_key": private_key_hex,
        "public_key": public_key_hex,
        "address": address
    }

    with open(WALLET_FILE, "w", encoding="utf-8") as f:
        json.dump(wallet_data, f, indent=2)

    print("[OK] Cartera creada")
    print("  Dirección:", address)


def load_wallet():
    if not os.path.exists(WALLET_FILE):
        print("[ERROR] No existe wallet.json, crea una primero")
        return None

    with open(WALLET_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def create_signed_tx():
    wallet = load_wallet()
    if wallet is None:
        return

    sender = wallet["address"]
    private_key_hex = wallet["private_key"]
    public_key_hex = wallet["public_key"]

    recipient = input("Dirección destino: ").strip()
    amount = int(input("Cantidad (entero): ").strip())
    nonce = int(input("Nonce (entero, empieza en 0 y ve subiendo): ").strip())

    sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)

    tx_dict = {
        "sender": sender,
        "recipient": recipient,
        "amount": amount,
        "nonce": nonce,
        "public_key": public_key_hex
    }

    # Mensaje a firmar
    msg = json.dumps(tx_dict, sort_keys=True).encode("utf-8")
    signature = sk.sign(msg).hex()

    tx_dict["signature"] = signature

    print("\n--- Transacción firmada (copia y pega en el nodo) ---")
    print(json.dumps(tx_dict, indent=2))
    print("----------------------------------------------------")


def main():
    print("1) Crear cartera nueva")
    print("2) Crear transacción firmada")
    choice = input("Opción: ").strip()

    if choice == "1":
        create_wallet()
    elif choice == "2":
        create_signed_tx()
    else:
        print("Opción no válida")


if __name__ == "__main__":
    main()

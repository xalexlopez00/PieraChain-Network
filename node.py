import json
import time
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any
from ecdsa import VerifyingKey, SECP256k1, BadSignatureError


def sha256_str(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Transaction:
    sender: str
    recipient: str
    amount: int
    nonce: int
    public_key: str
    signature: str
    timestamp: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "nonce": self.nonce,
            "public_key": self.public_key,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }

    def message_dict(self) -> Dict[str, Any]:
        # Lo que se firmó (sin la firma)
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "nonce": self.nonce,
            "public_key": self.public_key,
        }


@dataclass
class Block:
    index: int
    timestamp: float
    transactions: List[Transaction]
    previous_hash: str
    nonce: int = 0
    hash: str = ""

    def compute_hash(self) -> str:
        block_dict = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        block_string = json.dumps(block_dict, sort_keys=True)
        return sha256_str(block_string)


class Blockchain:
    def __init__(self, genesis_path: str, difficulty: int = 4):
        self.difficulty = difficulty
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.balances: Dict[str, int] = {}
        self.chain_id = ""
        self.nonces: Dict[str, int] = {}  # nonce por dirección

        self._load_genesis(genesis_path)

    def _load_genesis(self, genesis_path: str):
        with open(genesis_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.chain_id = data["chain_id"]
        self.balances = data["initial_balances"]

        g = data["genesis_block"]
        genesis_block = Block(
            index=g["index"],
            timestamp=time.time(),
            transactions=[],
            previous_hash=g["previous_hash"],
            nonce=g["nonce"],
            hash=g["hash"],
        )
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

        print(f"[INFO] Genesis hash: {genesis_block.hash}")
        print(f"[INFO] Chain ID: {self.chain_id}")

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def verify_signature(self, tx: Transaction) -> bool:
        try:
            vk = VerifyingKey.from_string(bytes.fromhex(tx.public_key), curve=SECP256k1)
        except Exception:
            print("[ERROR] Clave pública inválida")
            return False

        msg_dict = tx.message_dict()
        msg = json.dumps(msg_dict, sort_keys=True).encode("utf-8")

        try:
            vk.verify(bytes.fromhex(tx.signature), msg)
        except BadSignatureError:
            print("[ERROR] Firma inválida")
            return False

        # Comprobar que la dirección coincide con la clave pública
        derived_address = sha256_bytes(bytes.fromhex(tx.public_key))[:40]
        if derived_address != tx.sender:
            print("[ERROR] Dirección no coincide con la clave pública")
            return False

        return True

    def add_transaction_from_json(self, tx_json: str) -> bool:
        try:
            data = json.loads(tx_json)
        except json.JSONDecodeError:
            print("[ERROR] JSON inválido")
            return False

        tx = Transaction(
            sender=data["sender"],
            recipient=data["recipient"],
            amount=int(data["amount"]),
            nonce=int(data["nonce"]),
            public_key=data["public_key"],
            signature=data["signature"],
        )

        if not self.verify_signature(tx):
            return False

        # Nonce simple: debe ser el siguiente
        current_nonce = self.nonces.get(tx.sender, 0)
        if tx.nonce != current_nonce:
            print(f"[ERROR] Nonce incorrecto. Esperado {current_nonce}, recibido {tx.nonce}")
            return False

        sender_balance = self.balances.get(tx.sender, 0)
        if sender_balance < tx.amount:
            print("[ERROR] Saldo insuficiente")
            return False

        self.pending_transactions.append(tx)
        self.nonces[tx.sender] = current_nonce + 1
        print("[OK] Transacción añadida al mempool")
        return True

    def _apply_transactions(self, block: Block):
        for tx in block.transactions:
            self.balances[tx.sender] = self.balances.get(tx.sender, 0) - tx.amount
            self.balances[tx.recipient] = self.balances.get(tx.recipient, 0) + tx.amount

    def proof_of_work(self, block: Block) -> str:
        prefix = "0" * self.difficulty
        while True:
            hash_value = block.compute_hash()
            if hash_value.startswith(prefix):
                return hash_value
            block.nonce += 1

    def mine_block(self, miner_address: str, reward: int = 50) -> Block:
        # Recompensa de bloque (sin firma, tipo COINBASE)
        reward_tx = Transaction(
            sender="COINBASE",
            recipient=miner_address,
            amount=reward,
            nonce=0,
            public_key="",
            signature="",
        )
        block_txs = self.pending_transactions + [reward_tx]

        new_block = Block(
            index=self.last_block.index + 1,
            timestamp=time.time(),
            transactions=block_txs,
            previous_hash=self.last_block.hash,
        )

        print(f"[INFO] Minando bloque #{new_block.index}...")
        new_block.hash = self.proof_of_work(new_block)
        print(f"[INFO] Bloque minado: {new_block.hash}")

        self.chain.append(new_block)
        self._apply_transactions(new_block)
        self.pending_transactions = []
        return new_block

    def is_chain_valid(self) -> bool:
        prefix = "0" * self.difficulty

        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.previous_hash != previous.hash:
                print("[ERROR] previous_hash no coincide")
                return False

            if not current.hash.startswith(prefix):
                print("[ERROR] hash no cumple dificultad")
                return False

            if current.compute_hash() != current.hash:
                print("[ERROR] hash almacenado no coincide")
                return False

        return True


def main():
    bc = Blockchain("genesis.json", difficulty=4)

    while True:
        print("\n--- Nodo PieraChain ---")
        print("1) Ver saldos")
        print("2) Añadir transacción (pegar JSON firmado)")
        print("3) Minar bloque")
        print("4) Comprobar cadena")
        print("5) Salir")
        choice = input("Opción: ").strip()

        if choice == "1":
            print("Saldos:")
            for addr, bal in bc.balances.items():
                print(f"  {addr}: {bal}")
        elif choice == "2":
            print("Pega el JSON de la transacción (una línea):")
            tx_json = input()
            bc.add_transaction_from_json(tx_json)
        elif choice == "3":
            miner = input("Dirección del minero: ").strip()
            bc.mine_block(miner_address=miner, reward=50)
        elif choice == "4":
            print("Cadena válida:", bc.is_chain_valid())
        elif choice == "5":
            break
        else:
            print("Opción no válida")


if __name__ == "__main__":
    main()

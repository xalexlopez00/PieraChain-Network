import time, os, json, hashlib
from .models import Block, Transaction
from .wallet import Wallet

class Blockchain:
    def __init__(self):
        self.chain_file = "data/chain.json"
        self.mempool = []
        self.chain = []
        self.load_chain()

    def load_chain(self):
        if os.path.exists(self.chain_file):
            with open(self.chain_file, 'r') as f:
                self.chain = [Block(**b) for b in json.load(f)]
        else: self.create_genesis()

    def create_genesis(self):
        genesis = Block(index=0, timestamp=time.time(), transactions=[], proof=100, previous_hash="0")
        self.chain = [genesis]; self.save_chain()

    def save_chain(self):
        with open(self.chain_file, 'w') as f:
            json.dump([b.dict() for b in self.chain], f, indent=4)

    def get_balance(self, address: str):
        bal = 0
        for b in self.chain:
            for tx in b.transactions:
                if tx.recipient == address: bal += tx.amount
                if tx.sender == address: bal -= tx.amount
        return bal

    def mine_block(self, miner_address: str):
        last = self.chain[-1]
        proof = 0
        while not hashlib.sha256(f'{last.proof}{proof}'.encode()).hexdigest().startswith("0000"): proof += 1
        reward = Transaction(sender="SYSTEM", recipient=miner_address, amount=50, nonce=int(time.time()))
        self.mempool.append(reward)
        new_block = Block(index=len(self.chain), timestamp=time.time(), transactions=self.mempool, proof=proof, previous_hash=last.compute_hash())
        self.chain.append(new_block); self.mempool = []; self.save_chain()
        return new_block

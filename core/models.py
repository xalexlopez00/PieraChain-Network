from pydantic import BaseModel
from typing import List, Optional
import hashlib
import json

class Transaction(BaseModel):
    sender: str
    recipient: str
    amount: float
    nonce: int
    signature: Optional[str] = None

    def to_string(self) -> str:
        return f"{self.sender}{self.recipient}{self.amount}{self.nonce}"

class Block(BaseModel):
    index: int
    timestamp: float
    transactions: List[Transaction]
    proof: int
    previous_hash: str

    def compute_hash(self) -> str:
        block_string = json.dumps(self.dict(), sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

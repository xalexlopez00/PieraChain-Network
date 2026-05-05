import hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization

class Wallet:
    @staticmethod
    def generate_keys():
        private_key = ec.generate_private_key(ec.SECP256K1())
        public_key = private_key.public_key()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        address = hashlib.sha256(public_pem.encode()).hexdigest()[:32]
        return {"address": address, "private_key": private_pem, "public_key": public_pem}

    @staticmethod
    def verify_signature(public_key_pem: str, signature_hex: str, data: str) -> bool:
        try:
            pub_key = serialization.load_pem_public_key(public_key_pem.encode())
            pub_key.verify(bytes.fromhex(signature_hex), data.encode(), ec.ECDSA(hashes.SHA256()))
            return True
        except: return False

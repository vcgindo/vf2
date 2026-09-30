import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


secret_dir = Path(os.environ.get("USER_SERVICE_SECRET_DIR", "/run/secrets"))
private_path = secret_dir / "user-service-private-key.pem"
public_path = secret_dir / "user-service-public-key.pem"
ciphertext_path = secret_dir / "user-service-db-password.enc"
database_password = os.environ["USER_SERVICE_DATABASE_PASSWORD"].encode("utf-8")
secret_dir.mkdir(parents=True, exist_ok=True)

if not private_path.exists() or not public_path.exists():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
    public_path.write_bytes(private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
else:
    private_key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)

ciphertext = private_key.public_key().encrypt(
    database_password,
    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
)
ciphertext_path.write_text(base64.b64encode(ciphertext).decode("ascii"), encoding="utf-8")
for path in (private_path, public_path, ciphertext_path):
    os.chmod(path, 0o600)
    os.chown(path, 10001, 10001)
print("User-service local key material initialized")

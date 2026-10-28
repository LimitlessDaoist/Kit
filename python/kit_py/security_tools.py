from __future__ import annotations
import getpass, math, os, secrets, stat, string, subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from kit_py.auto_bootstrap import ensure_dependencies

MAGIC_HEADER = b"KITENC01"
SALT_LEN = 16
NONCE_LEN = 12
PBKDF2_ITERATIONS = 600_000
MAX_CRYPT_FILE_BYTES = 512 * 1024 * 1024
MAX_SHRED_FILE_BYTES = 2 * 1024 * 1024 * 1024

PASSPHRASE_WORDS = [
    "anchor", "apollo", "arctic", "atlas", "aurora", "avalon", "beacon", "bison",
    "breeze", "bronze", "canyon", "carbon", "castle", "cedar", "cobalt", "comet",
    "condor", "copper", "coral", "cosmos", "crater", "crimson", "cipher", "dagger",
    "delta", "desert", "dynamo", "eclipse", "ember", "emerald", "enigma", "epoch",
    "falcon", "fathom", "fjord", "flint", "forest", "fossil", "fusion", "galaxy",
    "garnet", "geyser", "glacier", "granite", "harbor", "helium", "horizon", "hunter",
    "indigo", "island", "jasper", "jungle", "kepler", "krypton", "lagoon", "lantern",
    "lithium", "magnet", "mantis", "marble", "matrix", "meadow", "mercury", "meteor",
    "monolith", "nebula", "neon", "nickel", "nimbus", "nomad", "nova", "obsidian",
    "omega", "onyx", "opal", "orbit", "orion", "osprey", "oxygen", "paladin",
    "panther", "paradox", "pegasus", "phoenix", "photon", "pioneer", "plasma", "polaris",
    "prism", "pulsar", "quantum", "quartz", "quasar", "raptor", "reactor", "redwood",
    "relic", "riptide", "rocket", "sapphire", "saturn", "scarlet", "seismic", "sentinel",
    "shadow", "sierra", "silicon", "silver", "solstice", "sonar", "spark", "spectra",
    "stealth", "stellar", "stratos", "summit", "tempest", "tensor", "terra", "thunder",
    "timber", "titan", "topaz", "torrent", "trident", "tundra", "turbine", "twilight",
    "typhoon", "umbra", "valkyrie", "vanguard", "vector", "velvet", "vertex", "vortex",
    "voyager", "vulcan", "warden", "whisper", "winter", "xenon", "zenith", "zephyr",
]
SYMBOLS = "!@#$%^&*()-_=+[]{}?"

def generate_passwords(
    length: int = 20,
    use_symbols: bool = True,
    passphrase: bool = False,
    words: int = 5,
    count: int = 1,
    copy_clip: bool = False,
) -> Dict[str, Any]:
    count = max(1, min(50, int(count)))
    generated: List[str] = []
    if passphrase:
        word_count = max(3, min(16, int(words or 5)))
        for _ in range(count):
            picked = [secrets.choice(PASSPHRASE_WORDS) for _ in range(word_count)]
            num_suffix = secrets.randbelow(900) + 100
            generated.append("-".join(picked) + f"-{num_suffix}")
        entropy_bits = round(word_count * math.log2(len(PASSPHRASE_WORDS)) + math.log2(900), 1)
    else:
        length = max(8, min(256, int(length)))
        alphabet = string.ascii_lowercase + string.ascii_uppercase + string.digits
        if use_symbols:
            alphabet += SYMBOLS
        for _ in range(count):
            chars = [
                secrets.choice(string.ascii_lowercase),
                secrets.choice(string.ascii_uppercase),
                secrets.choice(string.digits),
            ]
            if use_symbols:
                chars.append(secrets.choice(SYMBOLS))
            while len(chars) < length:
                chars.append(secrets.choice(alphabet))
            secrets.SystemRandom().shuffle(chars)
            generated.append("".join(chars))
        entropy_bits = round(length * math.log2(len(alphabet)), 1)

    for item in generated:
        print(item)
    print(f"\n[Entropy: ~{entropy_bits} bits | CSPRNG: os.urandom]")
    if copy_clip and generated:
        try:
            subprocess.run(["clip"], input=generated[0].encode("utf-16le"), check=True)
            print("Copied first password to clipboard.")
        except Exception:
            pass
    return {"items": generated, "entropy_bits": entropy_bits}

def _derive_key(password: str, salt: bytes) -> bytes:
    ensure_dependencies(packages=["cryptography"])
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=PBKDF2_ITERATIONS)
    return kdf.derive(password.encode("utf-8"))

def encrypt_file(input_path: Path, output_path: Optional[Path] = None, password: Optional[str] = None) -> Path:
    ensure_dependencies(packages=["cryptography"])
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    in_resolved = input_path.resolve()
    if not in_resolved.exists() or not in_resolved.is_file():
        raise FileNotFoundError(f"File not found: {in_resolved}")
    if in_resolved.stat().st_size > MAX_CRYPT_FILE_BYTES:
        raise ValueError("File exceeds 512 MB safety limit.")
    if not password:
        password = getpass.getpass("Enter encryption password: ")
        confirm = getpass.getpass("Confirm encryption password: ")
        if password != confirm:
            raise ValueError("Passwords do not match.")
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters.")
    output_path = output_path.resolve() if output_path else in_resolved.with_name(in_resolved.name + ".kitenc")
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    aesgcm = AESGCM(_derive_key(password, salt))
    ciphertext = aesgcm.encrypt(nonce, in_resolved.read_bytes(), MAGIC_HEADER)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(MAGIC_HEADER + salt + nonce + ciphertext)
    print(f"Encrypted (AES-256-GCM, 600k PBKDF2) -> {output_path}")
    return output_path

def decrypt_file(input_path: Path, output_path: Optional[Path] = None, password: Optional[str] = None) -> Path:
    ensure_dependencies(packages=["cryptography"])
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    in_resolved = input_path.resolve()
    if not in_resolved.exists() or not in_resolved.is_file():
        raise FileNotFoundError(f"File not found: {in_resolved}")
    blob = in_resolved.read_bytes()
    min_len = len(MAGIC_HEADER) + SALT_LEN + NONCE_LEN + 16
    if len(blob) < min_len or not blob.startswith(MAGIC_HEADER):
        raise ValueError("Not a valid .kitenc encrypted file (header mismatch).")
    if not password:
        password = getpass.getpass("Enter decryption password: ")
    offset = len(MAGIC_HEADER)
    salt = blob[offset : offset + SALT_LEN]
    nonce = blob[offset + SALT_LEN : offset + SALT_LEN + NONCE_LEN]
    ciphertext = blob[offset + SALT_LEN + NONCE_LEN :]
    aesgcm = AESGCM(_derive_key(password, salt))
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, MAGIC_HEADER)
    except InvalidTag as exc:
        raise ValueError("Decryption failed: wrong password or tampered file.") from exc
    if output_path is None:
        if in_resolved.name.endswith(".kitenc"):
            output_path = in_resolved.with_name(in_resolved.name[: -len(".kitenc")])
        else:
            output_path = in_resolved.with_name(in_resolved.stem + "_decrypted" + in_resolved.suffix)
    else:
        output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(plaintext)
    print(f"Decrypted -> {output_path}")
    return output_path

def shred_file(target_path: Path, passes: int = 3) -> Dict[str, Any]:
    passes = max(1, min(10, int(passes)))
    if target_path.is_symlink():
        raise ValueError("Security policy: refusing to shred a symbolic link.")
    resolved = target_path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {resolved}")
    if resolved.is_dir():
        raise ValueError("Security policy: `kit shred` only shreds individual files, not directories.")
    size = resolved.stat().st_size
    if size > MAX_SHRED_FILE_BYTES:
        raise ValueError("File exceeds 2 GB safety limit.")
    try:
        os.chmod(resolved, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass
    chunk_size = 64 * 1024
    with open(resolved, "r+b", buffering=0) as f:
        for p in range(passes):
            f.seek(0)
            remaining = size
            is_zero = (p == passes - 1 and passes > 1)
            while remaining > 0:
                n = min(chunk_size, remaining)
                f.write((b"\x00" * n) if is_zero else os.urandom(n))
                remaining -= n
            f.flush()
            os.fsync(f.fileno())
    obfuscated = resolved.with_name(f".shred_{secrets.token_hex(8)}.tmp")
    resolved.rename(obfuscated)
    obfuscated.unlink()
    print(f"Shredded and destroyed '{resolved.name}' ({size} bytes, {passes} passes).")
    return {"shredded": str(resolved), "bytes": size, "passes": passes}


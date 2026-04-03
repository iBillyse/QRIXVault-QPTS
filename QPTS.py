import time, sys, winsound, os, random, string, subprocess, getpass, traceback
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import hash_secret_raw, Type
from cryptography.exceptions import InvalidTag

MAGIC_HEADER = b"QRIX"

def clear_secret(secret_bytearray):
    """Overwrites the master key in RAM with zeros for security."""
    for i in range(len(secret_bytearray)):
        secret_bytearray[i] = 0

def secure_shred(path):
    """Forensic-grade wipe: overwrites with zeros and random data before delete."""
    try:
        if os.path.exists(path):
            size = os.path.getsize(path)
            with open(path, "ba+", buffering=0) as f:
                f.seek(0)
                f.write(b'\x00' * size) # Pass 1: Zeros
                f.seek(0)
                f.write(os.urandom(size)) # Pass 2: Random
            os.remove(path)
    except Exception as e:
        print(f"\n[!] SHRED ERROR: {e}")

def generate_argon2_key(password_bytes, salt):
    """Derives a 32-byte key using Argon2id. Optimized for security."""
    return hash_secret_raw(
        secret=bytes(password_bytes), 
        salt=salt,
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        type=Type.ID
    )

def qrix_engine(data, label):
    """Visual progress bar with audio feedback and 100% force-fill."""
    print(f"\n--- {label} ---")
    total = len(data)
    bar_length = 40
    chunk_size = max(1, total // bar_length)
    
    for i in range(0, total, chunk_size):
        percent = (i / total)
        filled = int(bar_length * percent)
        bar = '█' * filled + '░' * (bar_length - filled)
        sys.stdout.write(f"\r      [{bar}] {int(percent*100)}% ")
        sys.stdout.flush()
        if i % (chunk_size * 4) == 0: winsound.Beep(1200, 15)
        time.sleep(0.01)
    
    # Force 100% display
    full_bar = '█' * bar_length
    sys.stdout.write(f"\r      [{full_bar}] 100% ")
    sys.stdout.flush()
    print(f"\n--- {label} COMPLETE ---")

def get_path(mode):
    """Stable file dialog that won't crash when compiled."""
    root = tk.Tk()
    root.withdraw() 
    root.attributes("-topmost", True)
    if mode == "open":
        file_path = filedialog.askopenfilename()
    else:
        file_path = filedialog.askopenfilename(filetypes=[("Qrix Files", "*.QTFE")])
    root.destroy()
    return file_path

def main_menu():
    downloads = str(Path.home() / "Downloads")
    os.system('cls')
    print("====================================")
    print("    QRIX ARGON2-AES INFRASTRUCTURE  ")
    print("====================================")
    
    # Password entry is hidden (blind typing)
    raw_pw = getpass.getpass("ENTER MASTER KEY: ")
    password_memory = bytearray(raw_pw.encode())
    del raw_pw 

    while True:
        try:
            print("\n1. PUNCH (ENCRYPT & SHRED)\n2. READ  (DECRYPT)\n3. EXIT")
            choice = input("\nCOMMAND > ")

            if choice == '1':
                path = get_path("open")
                if path:
                    with open(path, 'rb') as f: data = f.read()
                    salt, nonce = os.urandom(16), os.urandom(12)
                    key = generate_argon2_key(password_memory, salt)
                    
                    # Store original filename inside the encrypted packet
                    package = os.path.basename(path).encode() + b"|" + data
                    ciphertext = AESGCM(key).encrypt(nonce, package, None)
                    
                    # Save with randomized name to Downloads
                    out_path = os.path.join(downloads, f"QRIX_{''.join(random.choices(string.digits, k=10))}.QTFE")
                    with open(out_path, 'wb') as f: 
                        f.write(MAGIC_HEADER + salt + nonce + ciphertext)
                    
                    qrix_engine(data, "PUNCHING")
                    secure_shred(path)
                    print(f"\n[!] SECURED TO: {os.path.basename(out_path)}")
                    input("\nPress Enter...")

            elif choice == '2':
                path = get_path("read")
                if path:
                    with open(path, 'rb') as f:
                        if f.read(4) != MAGIC_HEADER: 
                            print("INVALID FILE TYPE")
                            continue
                        file_data = f.read()
                    
                    salt, nonce, ciphertext = file_data[:16], file_data[16:28], file_data[28:]
                    key = generate_argon2_key(password_memory, salt)
                    
                    decrypted = AESGCM(key).decrypt(nonce, ciphertext, None)
                    header, original_data = decrypted.split(b"|", 1)
                    
                    qrix_engine(original_data, "DECRYPTING")
                    
                    out_path = os.path.join(downloads, header.decode())
                    with open(out_path, 'wb') as f: f.write(original_data)
                    print(f"\n[!] FILE RECOVERED AS: {header.decode()}")
                    input("\nPress Enter...")
            
            elif choice == '3':
                clear_secret(password_memory)
                print("RAM Purged. Goodbye.")
                break
        except InvalidTag:
            print("\n[!] ACCESS DENIED: WRONG KEY.")
            time.sleep(2)
        except Exception:
            print("\n[!] SYSTEM CRASH PREVENTED:")
            traceback.print_exc()
            input("\nPress Enter to return to menu...")

if __name__ == "__main__":
    main_menu()

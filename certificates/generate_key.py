from cryptography.fernet import Fernet
import os

def generate_symmetric_key(output_path="certificates/symmetric.key"):
    # Crear carpeta si no existe
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Generar y guardar la clave
    key = Fernet.generate_key()
    with open(output_path, "wb") as key_file:
        key_file.write(key)
    print(f"✅ Clave simétrica generada en: {output_path}")

if __name__ == "__main__":
    generate_symmetric_key()

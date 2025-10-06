"""
Generador de 2 llaves para cifrado asimetrico
"""

#!/usr/bin/env python3
import sys
from pathlib import Path

try:
    from OpenSSL import crypto
except ImportError as e:
    print(f"Error importando OpenSSL: {e}")
    print("OpenSSL no está instalado. Ejecuta: pip3 install pyopenssl")
    sys.exit(1)

def generate_self_signed_cert(cert_dir="certificates"):
    
    # Crear directorio si no existe (compatible con Windows)
    cert_path = Path(cert_dir)
    cert_path.mkdir(exist_ok=True)

    key_file = cert_path / "server.key"
    cert_file = cert_path / "server.crt"
    
    if key_file.exists() and cert_file.exists():
        return True
    
    try:
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)
    
        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "State"
        cert.get_subject().L = "City"
        cert.get_subject().O = "Organization"
        cert.get_subject().OU = "Organizational Unit"
        cert.get_subject().CN = "localhost"  
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(60*24*60*60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(key, 'sha256')
        
        with open(key_file, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

        with open(cert_file, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        return True
        
    except Exception as e:
        print(f"Error generando certificados: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = generate_self_signed_cert()
    if success:
        print("Generación de certificados COMPLETADA")
    else:
        print("Generación de certificados FALLÓ")
        sys.exit(1)
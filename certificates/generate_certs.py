#!/usr/bin/env python3
"""
Script para generar certificados SSL auto-firmados para desarrollo
Compatible con Linux y Windows
"""

import os
import sys
from pathlib import Path

try:
    from OpenSSL import crypto
    print("OpenSSL importado correctamente")
except ImportError as e:
    print(f"Error importando OpenSSL: {e}")
    print("OpenSSL no está instalado. Ejecuta: pip3 install pyopenssl")
    sys.exit(1)

def generate_self_signed_cert(cert_dir="certificates"):
    """Genera certificado SSL auto-firmado para desarrollo"""
    
    print(f"🔧 Iniciando generación de certificados en: {cert_dir}")
    
    # Crear directorio si no existe (compatible con Windows)
    cert_path = Path(cert_dir)
    cert_path.mkdir(exist_ok=True)
    print(f"Directorio creado/verificado: {cert_path.absolute()}")
    
    # Rutas de los archivos
    key_file = cert_path / "server.key"
    cert_file = cert_path / "server.crt"
    
    print(f"🔧 Ruta clave: {key_file}")
    print(f"🔧 Ruta certificado: {cert_file}")
    
    # Verificar si ya existen
    if key_file.exists() and cert_file.exists():
        print("✅ Los certificados ya existen en el directorio")
        print(f"   Certificado: {cert_file}")
        print(f"   Clave: {key_file}")
        return True
    
    try:
        print("🔧 Generando clave privada...")
        # Generar clave privada
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)
        
        print("🔧 Creando certificado...")
        # Crear certificado
        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "State"
        cert.get_subject().L = "City"
        cert.get_subject().O = "Organization"
        cert.get_subject().OU = "Organizational Unit"
        cert.get_subject().CN = "localhost"  # Importante para SSL
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365*24*60*60)  # Válido por 1 año
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(key, 'sha256')
        
        print("🔧 Guardando archivos...")
        # Guardar clave privada
        with open(key_file, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
        
        # Guardar certificado
        with open(cert_file, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        
        print(f"Certificado generado: {cert_file}")
        print(f"Clave privada generada: {key_file}")
        print("NOTA: Estos certificados son para DESARROLLO, no para producción")
        return True
        
    except Exception as e:
        print(f"Error generando certificados: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Ejecutando generador de certificados...")
    success = generate_self_signed_cert()
    if success:
        print("Generación de certificados COMPLETADA")
    else:
        print("Generación de certificados FALLÓ")
        sys.exit(1)
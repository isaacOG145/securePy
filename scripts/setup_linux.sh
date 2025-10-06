#!/bin/bash
echo "Configurando Secure Chat en Linux..."

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
echo "Actualizando pip..."
pip3 install --upgrade pip3

# Instalar dependencias
echo "Instalando dependencias..."
pip3 install -r requirements.txt

pip3 install cryptography

# Generar certificados (con el script corregido)
echo "Generando certificados SSL..."
python3 certificates/generate_certs.py

echo "Configuración completada!"
echo "Para activar el entorno virtual en el futuro ejecuta: source venv/bin/activate"
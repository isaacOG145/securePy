# securePy

Repositorio para el proyecto de seguridad informatica 

Pre-requisitos
Python 3.8 o superior
pip (gestor de paquetes de Python)

Instalación 

Linux-mac
# Dar permisos de ejecución al script de instalación
chmod +x scripts/setup_linux.sh

# Ejecutar el setup completo
./scripts/setup_linux.sh

windows
# Ejecutar el script de instalación
scripts\setup_windows.bat

Instalación manual

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate.bat

# Instalar dependencias
pip install -r requirements.txt

# Generar certificados SSL
python certificates/generate_certs.py

Recursos Utilizados
Python 3.13.5
Librerías Principales:
SSL - Encriptación y seguridad de comunicaciones

socket - Comunicación en red

threading - Manejo de múltiples clientes

pyside6 - Interfaz gráfica moderna

sys - Funcionalidades del sistema

Dependencias 

PySide6>=6.5.0        # Interfaz gráfica
pyopenssl>=23.2.0     # Manejo de certificados SSL
cryptography>=41.0.0  # Criptografía
pyyaml>=6.0          # Configuración

Iniciar la aplicación 

# Activar entorno virtual (siempre necesario)
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate.bat # Windows

# Ejecutar la aplicación
python main.py

Modos de ejecución

# Cliente con interfaz gráfica (por defecto)
python main.py --mode gui

# Solo servidor
python main.py --mode server

# Cliente de consola
python main.py --mode client

# Configuración personalizada
python main.py --config config/development.yaml
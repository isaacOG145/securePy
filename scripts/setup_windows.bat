
@echo off
echo Configurando Secure Chat en Windows...

:: Crear entorno virtual si no existe
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)

:: Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

:: Actualizar pip
echo Actualizando pip...
pip install --upgrade pip

:: Instalar dependencias
echo Instalando dependencias...
pip install -r requirements.txt

:: Generar certificados
echo Generando certificados SSL...
python certificates\generate_certs.py

echo Configuración completada!
echo Para activar el entorno virtual en el futuro ejecuta: venv\Scripts\activate.bat
pause

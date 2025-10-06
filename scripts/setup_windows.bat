@echo off
echo 🔧 Configurando Secure Chat en Windows...

:: Verificar si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python no encontrado en el PATH
    echo Por favor instala Python desde https://python.org/downloads
    echo Asegúrate de marcar "Add Python to PATH" durante la instalación
    pause
    exit /b 1
)

:: Verificar versión de Python
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python %PYTHON_VERSION% detectado

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
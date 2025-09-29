import socket
import threading
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QScrollArea, QLabel, QInputDialog, QMessageBox, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QFont, QColor

# --- 1. CLASE PARA MANEJAR LA RECEPCIÓN DE RED CON SIGNALS Y SLOTS ---

class WorkerReceiver(QObject):
    """Objeto que se ejecuta en un hilo separado para recibir datos del socket."""
    
    message_received = Signal(str)
    connection_lost = Signal()
    
    def __init__(self, socket, parent=None):
        super().__init__(parent)
        self.socket_cliente = socket
        self.running = True

    def run(self):
        """Loop principal de recepción de mensajes."""
        while self.running:
            try:
                mensaje = self.socket_cliente.recv(1024).decode('utf-8')
                if mensaje:
                    self.message_received.emit(mensaje)
                else:
                    self.connection_lost.emit()
                    break
            except socket.error:
                self.connection_lost.emit()
                break
            except Exception:
                self.connection_lost.emit()
                break
    
    def stop(self):
        """Detiene el bucle de recepción."""
        self.running = False

# --- 2. CLASE PRINCIPAL DE LA GUI ---

class ClienteChat(QMainWindow):
    
    def __init__(self, host='localhost', puerto=9999):
        super().__init__()
        self.host = host
        self.puerto = puerto
        self.socket_cliente = None
        self.nombre_usuario = ""
        self.conectado = False
        
        self.setWindowTitle("SecurePy Chat (PySide6)")
        self.resize(550, 750) 
        self.setMinimumSize(400, 600)
        
        self.setup_ui()
        self.iniciar_chat()

    def setup_ui(self):
        """Configura la ventana principal y sus widgets."""
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal vertical (contenedor de toda la ventana)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Header Bar Personalizado ---
        # El texto inicial será para pedir el nombre
        self.header_label = QLabel("Ingresa tu nombre para iniciar chat") 
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_label.setFixedHeight(50)
        self.header_label.setStyleSheet("""
            QLabel {
                background-color: #075E54; /* Verde de WhatsApp */
                color: white;
                font-size: 14pt;
                font-weight: bold;
                padding: 10px;
            }
        """)
        self.main_layout.addWidget(self.header_label)
        # -----------------------------------------------------------

        # 1. Área de Chat (Historial) - Scrollable y Expandible
        self.chat_area = QWidget()
        self.chat_area_layout = QVBoxLayout(self.chat_area)
        self.chat_area_layout.setAlignment(Qt.AlignmentFlag.AlignTop) 
        self.chat_area_layout.setSpacing(5)
        self.chat_area_layout.setContentsMargins(10, 10, 10, 10)
        
        # Spacer para asegurar que los mensajes estén siempre arriba
        self.chat_area_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.chat_area)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.main_layout.addWidget(self.scroll_area)

        # 2. Área de Entrada de Mensajes
        self.input_widget = QWidget()
        self.input_layout = QHBoxLayout(self.input_widget)
        self.input_layout.setContentsMargins(10, 5, 10, 10)
        self.input_layout.setSpacing(8)

        # Campo de entrada
        self.entry_field = QLineEdit()
        self.entry_field.setPlaceholderText("Escribe tu mensaje o /quit para salir...")
        self.entry_field.returnPressed.connect(self.enviar_mensaje_gui)
        
        # Botón de enviar
        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self.enviar_mensaje_gui)

        self.input_layout.addWidget(self.entry_field)
        self.input_layout.addWidget(self.send_button)
        self.main_layout.addWidget(self.input_widget)
        
        # --- ESTILO CSS MEJORADO ---
        self.setStyleSheet("""
            QMainWindow { background-color: #ECE5DD; } 
            
            QScrollArea { 
                border: none; 
                background-color: #F8F9FA; 
            }
            
            QLineEdit { 
                border: 1px solid #CCCCCC; 
                border-radius: 20px; 
                padding: 10px 18px; 
                background-color: white;
                min-height: 25px;
            }
            
            QPushButton {
                background-color: #075E54; 
                color: white; 
                border-radius: 20px; 
                padding: 10px 15px;
                font-weight: bold;
                min-width: 80px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #054a3e;
            }
        """)

    def conectar_servidor(self):
        """Establece conexión con el servidor."""
        try:
            self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_cliente.connect((self.host, self.puerto))
            self.conectado = True
            self.mostrar_mensaje_sistema(f"✅ Conectado al servidor {self.host}:{self.puerto}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error de Conexión", f"❌ No se pudo conectar al servidor: {e}")
            return False

    def mostrar_mensaje_sistema(self, mensaje):
        """Muestra un mensaje del sistema (centro, texto simple) fuera de las burbujas."""
        label = QLabel(f"--- {mensaje} ---")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # --- CÓDIGO CORREGIDO: Inicialización correcta de QFont ---
        font = QFont("Arial", 9)
        font.setItalic(True) # Se establece la cursiva con el método correcto
        label.setFont(font)
        # --------------------------------------------------------
        
        label.setStyleSheet("color: #666;")
        self.chat_area_layout.addWidget(label)
        self.scroll_to_bottom()

    def crear_burbuja(self, texto, is_mine):
        """Crea un widget con estilo de burbuja."""
        
        burbuja_frame = QWidget()
        burbuja_layout = QHBoxLayout(burbuja_frame)
        burbuja_layout.setContentsMargins(0, 0, 0, 0)
        burbuja_layout.setSpacing(0)

        label = QLabel(texto)
        label.setWordWrap(True)
        label.setMinimumHeight(20)

        bubble_css = f"""
            QLabel {{
                background-color: {'#DCF8C6' if is_mine else '#FFFFFF'}; 
                color: black;
                border-radius: 12px;
                padding: 8px 12px;
                margin: 0px; 
                font-size: 10pt;
            }}
        """
        label.setStyleSheet(bubble_css)
        label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        
        if is_mine:
            burbuja_layout.addStretch(1)
            burbuja_layout.addWidget(label)
            burbuja_layout.addSpacing(5)
        else:
            burbuja_layout.addSpacing(5)
            burbuja_layout.addWidget(label)
            burbuja_layout.addStretch(1)
        
        self.chat_area_layout.addWidget(burbuja_frame)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        """Asegura que el historial se desplace hasta el final."""
        QApplication.processEvents()
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    # --- SLOTS (Manejadores de Señales) ---

    def handle_received_message(self, mensaje):
        """Maneja los mensajes recibidos desde el hilo de red (WorkerReceiver)."""
        
        if mensaje.startswith(f"🌟 {self.nombre_usuario}") or mensaje.startswith("Bienvenido al chat,"):
            self.mostrar_mensaje_sistema(mensaje)
        elif mensaje.startswith(f"{self.nombre_usuario}: "):
             pass 
        elif mensaje.startswith(("🌟", "👋", "👥")):
            self.mostrar_mensaje_sistema(mensaje)
        else:
            self.crear_burbuja(mensaje, is_mine=False)

    def enviar_mensaje_gui(self):
        """Función llamada por el botón o la tecla Enter para enviar el mensaje."""
        mensaje = self.entry_field.text()
        self.entry_field.clear()

        if not self.conectado or not mensaje.strip():
            return
            
        if mensaje.lower() == '/quit':
            self.socket_cliente.send('/quit'.encode('utf-8'))
            self.close()
            return

        try:
            self.socket_cliente.send(mensaje.encode('utf-8'))
            self.crear_burbuja(f"Tú: {mensaje}", is_mine=True) 
        except Exception as e:
            QMessageBox.critical(self, "Error de Envío", f"Error al enviar: {e}")

    # --- LÓGICA DE CONEXIÓN E INICIO ---

    def iniciar_chat(self):
        """Maneja la conexión, NICK y el inicio de hilos."""
        # Al iniciar, la barra ya dice "Ingresa el nombre de usuario"
        if not self.conectar_servidor():
            return

        try:
            mensaje_servidor = self.socket_cliente.recv(1024).decode('utf-8')
            
            if mensaje_servidor == "NICK":
                # La ventana de diálogo aparece DESPUÉS de conectar y recibir la solicitud NICK
                name, ok = QInputDialog.getText(self, "Nombre de Usuario", 
                                                "Ingresa tu nombre de usuario para el chat:")

                if ok and name.strip():
                    self.nombre_usuario = name.strip()
                else:
                    self.nombre_usuario = "Anonimo_PySide"
                    
                self.socket_cliente.send(self.nombre_usuario.encode('utf-8'))
                
                # ACTUALIZACIÓN CLAVE: Se actualiza el Header Label con el nombre ingresado
                self.header_label.setText(f"Chat: {self.nombre_usuario}")
                self.setWindowTitle(f"SecurePy Chat - {self.nombre_usuario}") 
            else:
                self.mostrar_mensaje_sistema("Error: El servidor no solicitó NICK.")
                self.conectado = False
                self.cerrar_conexion()
                return
        except Exception as e:
            self.mostrar_mensaje_sistema(f"Error al configurar nombre de usuario: {e}")
            self.conectado = False
            self.cerrar_conexion()
            return
            
        # Iniciar el hilo de recepción
        self.thread = QThread()
        self.worker = WorkerReceiver(self.socket_cliente)
        self.worker.moveToThread(self.thread)
        
        self.thread.started.connect(self.worker.run)
        self.worker.message_received.connect(self.handle_received_message)
        self.worker.connection_lost.connect(self.cerrar_conexion_ordenada)
        
        self.thread.start()

    def cerrar_conexion_ordenada(self):
        """Slot llamado cuando el hilo de red indica que se perdió la conexión."""
        if self.conectado:
            self.mostrar_mensaje_sistema("❌ Conexión con el servidor perdida.")
        self.cerrar_conexion()

    def cerrar_conexion(self):
        """Cierra el socket y detiene los hilos."""
        if self.conectado:
            self.conectado = False
            try:
                self.socket_cliente.send('/quit'.encode('utf-8'))
                self.socket_cliente.close()
            except:
                pass
        
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            
        self.close()

    def closeEvent(self, event):
        """Manejador para el evento de cerrar ventana (botón X)."""
        if self.conectado:
            reply = QMessageBox.question(self, 'Salir', 
                "¿Quieres cerrar la sesión de chat?", 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.cerrar_conexion()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    chat_client = ClienteChat(host='localhost', puerto=9999)
    chat_client.show()
    sys.exit(app.exec())
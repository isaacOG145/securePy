import socket
import ssl
import threading
import time
import sys
from typing import Optional, Callable
from pathlib import Path

try:

    from .protocol import (
        MessageType, CommandType, ChatMessage, SystemMessage,
        ErrorMessage, MessageFactory, ProtocolValidator
    )
except ImportError:
    
    from protocol import (
        MessageType, CommandType, ChatMessage, SystemMessage,
        ErrorMessage, MessageFactory, ProtocolValidator
    )


class SecureChatClient:
    
    def __init__(self, host: str = 'localhost', port: int = 9999,
                 username: str = None):
    
        self.host = host
        self.port = port
        self.username = username
        
        self.connected = False
        self.authenticated = False
        self.socket: Optional[ssl.SSLSocket] = None
        
        self.on_message_received: Optional[Callable] = None
        self.on_connection_changed: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        self.receive_thread: Optional[threading.Thread] = None
        
    def initialize_ssl_context(self) -> ssl.SSLContext:
        
        try:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = False  
            context.verify_mode = ssl.CERT_NONE 
            
            return context
            
        except Exception as e:
            self._handle_error(f"Error configurando SSL: {e}")
            raise
    
    def connect(self) -> bool:
        
        try:
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            ssl_context = self.initialize_ssl_context()
            self.socket = ssl_context.wrap_socket(
                sock, server_hostname=self.host
            )
            
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            print(f"Conectado al servidor seguro {self.host}:{self.port}")
            
            self.receive_thread = threading.Thread(
                target=self._receive_messages,
                daemon=True
            )
            self.receive_thread.start()
            
            self._notify_connection_changed(True)
            
            if self.username:
                return self._authenticate()
            
            return True
            
        except Exception as e:
            self._handle_error(f"Error conectando al servidor: {e}")
            return False
    
    def _authenticate(self) -> bool:
        
        try:
            if not self.username:
                self._handle_error("No se especificó nombre de usuario")
                return False
            
            auth_message = MessageFactory.create_auth_message(self.username)
            self.socket.send(auth_message.to_json().encode('utf-8'))
            
            print(f"Autenticando como: {self.username}")
            return True
            
        except Exception as e:
            self._handle_error(f"Error en autenticación: {e}")
            return False
    
    def send_message(self, content: str, room: str = "general") -> bool:
        
        try:
            if not self.connected or not self.socket:
                self._handle_error("No conectado al servidor")
                return False
            
            if not self.authenticated and self.username:
                self._handle_error("No autenticado en el servidor")
                return False
            
            sanitized_content = ProtocolValidator.sanitize_content(content)
            
            chat_message = MessageFactory.create_chat_message(
                self.username or "Anónimo",
                sanitized_content,
                room
            )
            
            self.socket.send(chat_message.to_json().encode('utf-8'))
            return True
            
        except Exception as e:
            self._handle_error(f"Error enviando mensaje: {e}")
            return False
    
    def send_command(self, command: CommandType, **params) -> bool:

        try:
            if not self.connected or not self.socket:
                self._handle_error("No conectado al servidor")
                return False
            
            command_message = MessageFactory.create_command_message(
                self.username or "Anónimo",
                command,
                params
            )
            
            self.socket.send(command_message.to_json().encode('utf-8'))
            return True
            
        except Exception as e:
            self._handle_error(f"Error enviando comando: {e}")
            return False
    
    def _receive_messages(self):
        """Hilo para recibir mensajes del servidor"""
        while self.connected and self.socket:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break  # Servidor desconectado
                
                # Procesar mensaje recibido
                self._process_received_message(data)
                
            except socket.timeout:
                continue
            except (ssl.SSLError, ConnectionResetError, BrokenPipeError):
                break
            except Exception as e:
                self._handle_error(f"Error recibiendo mensaje: {e}")
                break
        
        # Conexión perdida
        self.disconnect()
    
    def _process_received_message(self, message_data: str):
        """Procesa un mensaje recibido del servidor"""
        try:
            if not ProtocolValidator.validate_message(message_data):
                print(f"Mensaje inválido recibido: {message_data}")
                return
            
            message = ChatMessage.from_json(message_data)
            
            # Procesar según el tipo de mensaje
            if message.type == MessageType.SYSTEM:
                self._handle_system_message(message)
            elif message.type == MessageType.CHAT:
                self._handle_chat_message(message)
            elif message.type == MessageType.ERROR:
                self._handle_error_message(message)
            else:
                print(f"📨 Mensaje no manejado ({message.type}): {message.content}")
            
            # Notificar callback si está configurado
            if self.on_message_received:
                self.on_message_received(message)
                
        except Exception as e:
            self._handle_error(f"Error procesando mensaje: {e}")
    
    def _handle_system_message(self, message: SystemMessage):
        """Maneja mensajes del sistema"""
        level = message.metadata.get('level', 'info') if message.metadata else 'info'
        
        if level == 'error':
            print(f"Sistema: {message.content}")
        elif level == 'warning':
            print(f"Sistema: {message.content}")
        else:
            print(f"ℹSistema: {message.content}")
        
        # Detectar mensajes de autenticación exitosa
        if "se ha unido al chat" in message.content and self.username in message.content:
            self.authenticated = True
            print(f"Autenticación exitosa como {self.username}")
    
    def _handle_chat_message(self, message: ChatMessage):
        """Maneja mensajes de chat normales"""
        room = message.metadata.get('room', 'general') if message.metadata else 'general'
        print(f"[{room}] {message.sender}: {message.content}")
    
    def _handle_error_message(self, message: ErrorMessage):
        """Maneja mensajes de error"""
        error_code = message.metadata.get('error_code', 'UNKNOWN') if message.metadata else 'UNKNOWN'
        print(f"Error ({error_code}): {message.content}")
    
    def _notify_connection_changed(self, connected: bool):
        """Notifica cambio en el estado de conexión"""
        if self.on_connection_changed:
            self.on_connection_changed(connected)
    
    def _handle_error(self, error_message: str):
        """Maneja errores internos"""
        print(f"{error_message}")
        if self.on_error:
            self.on_error(error_message)
    
    def disconnect(self):
        """Desconecta del servidor de forma segura"""
        if self.connected:
            print("🔌 Desconectando del servidor...")
            
            # Enviar comando de salida si está autenticado
            if self.authenticated:
                try:
                    self.send_command(CommandType.QUIT)
                except:
                    pass
            
            self.connected = False
            self.authenticated = False
            
            # Cerrar socket
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                finally:
                    self.socket = None
            
            # Notificar cambio de conexión
            self._notify_connection_changed(False)
            print("Desconectado del servidor")
    
    def set_callbacks(self, 
                     on_message_received: Callable = None,
                     on_connection_changed: Callable = None,
                     on_error: Callable = None):
        """
        Configura callbacks para eventos del cliente
        
        Args:
            on_message_received: Callback para mensajes recibidos
            on_connection_changed: Callback para cambios de conexión
            on_error: Callback para errores
        """
        self.on_message_received = on_message_received
        self.on_connection_changed = on_connection_changed
        self.on_error = on_error

# Cliente de consola simple para pruebas
class ConsoleChatClient:
    """Cliente de consola simple para pruebas"""
    
    def __init__(self, host: str = 'localhost', port: int = 9999):
        self.client = SecureChatClient(host, port)
        self.setup_callbacks()
    
    def setup_callbacks(self):
        """Configura los callbacks del cliente"""
        self.client.on_message_received = self._on_message_received
        self.client.on_connection_changed = self._on_connection_changed
        self.client.on_error = self._on_error
    
    def _on_message_received(self, message: ChatMessage):
        """Callback para mensajes recibidos"""
        # Ya se maneja en los métodos específicos del cliente base
        pass
    
    def _on_connection_changed(self, connected: bool):
        """Callback para cambios de conexión"""
        status = "conectado" if connected else "desconectado"
        print(f"Estado de conexión: {status}")
    
    def _on_error(self, error_message: str):
        """Callback para errores"""
        print(f"Error: {error_message}")
    
    def start(self):
        """Inicia el cliente de consola"""
        print("Iniciando cliente de consola Secure Chat")
        
        # Solicitar nombre de usuario
        username = input("Ingresa tu nombre de usuario: ").strip()
        if not username:
            username = f"Usuario_{int(time.time())}"
        
        self.client.username = username
        
        # Conectar al servidor
        if not self.client.connect():
            print("No se pudo conectar al servidor")
            return
        
        print(f"Chat iniciado como: {username}")
        print("Comandos disponibles:")
        print("  /users - Listar usuarios conectados")
        print("  /quit - Salir del chat")
        print("  Escribe tu mensaje y presiona Enter para enviar")
        print("-" * 50)
        
        try:
            # Loop principal de entrada
            while self.client.connected:
                try:
                    message = input().strip()
                    
                    if not message:
                        continue
                    
                    # Comandos especiales
                    if message.startswith('/'):
                        if message.lower() == '/quit':
                            break
                        elif message.lower() == '/users':
                            self.client.send_command(CommandType.LIST_USERS)
                        else:
                            print("Comando no reconocido")
                    else:
                        # Mensaje normal
                        self.client.send_message(message)
                        
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
                    
        except KeyboardInterrupt:
            print("\nCliente interrumpido por el usuario")
        finally:
            self.client.disconnect()

# Ejemplo de uso
if __name__ == "__main__":
    
    # Cliente de consola simple
    if len(sys.argv) > 1:
        host = sys.argv[1]
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 9999
    else:
        host = 'localhost'
        port = 9999
    
    # En Linux usar python3
    client = ConsoleChatClient(host, port)
    client.start()
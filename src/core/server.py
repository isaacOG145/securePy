"""
Servidor modular para Secure Chat
Maneja conexiones SSL y procesa mensajes usando el protocolo definido
"""

import socket
import ssl
import threading
import time
import logging
import platform
from typing import Dict, List, Optional, Set
from pathlib import Path

try:
    from .protocol import (
        MessageType, CommandType, ChatMessage, SystemMessage, 
        ErrorMessage, MessageFactory, ProtocolValidator
    )
except ImportError:
    # Para cuando se ejecuta directamente
    from protocol import (
        MessageType, CommandType, ChatMessage, SystemMessage, 
        ErrorMessage, MessageFactory, ProtocolValidator
    )


class ClientConnection:
    """Representa una conexión de cliente individual"""
    
    def __init__(self, client_socket: ssl.SSLSocket, address: tuple, username: str = ""):
        self.socket = client_socket
        self.address = address
        self.username = username
        self.connected = True
        self.authenticated = False
        self.last_activity = time.time()


class ChatRoom:
    """Representa una sala de chat"""
    
    def __init__(self, name: str):
        self.name = name
        self.clients: Set[ClientConnection] = set()
        self.created_at = time.time()


class SecureChatServer:
    """
    Servidor principal de chat seguro con SSL
    """
    
    def __init__(self, host: str = 'localhost', port: int = 9999, 
                 certfile: str = None, 
                 keyfile: str = None):
        """
        Inicializa el servidor seguro
        """
        self.host = host
        self.port = port
        
        # Rutas por defecto para certificados
        if certfile is None:
            certfile = 'certificates/server.crt'
        if keyfile is None:
            keyfile = 'certificates/server.key'
            
        self.certfile = certfile
        self.keyfile = keyfile
        
        # Estado del servidor
        self.running = False
        self.server_socket: Optional[ssl.SSLSocket] = None
        
        # Gestión de clientes y salas
        self.clients: Dict[ssl.SSLSocket, ClientConnection] = {}
        self.rooms: Dict[str, ChatRoom] = {"general": ChatRoom("general")}
        self.usernames: Set[str] = set()
        
        # Configuración de logging
        self.setup_logging()
        
    def setup_logging(self):
        """Configura el sistema de logging"""
        # Para Windows, usar formato simple sin emojis
        if platform.system() == 'Windows':
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        else:
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('logs/server.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('SecureChatServer')
        
    def initialize_ssl_context(self) -> ssl.SSLContext:
        """Inicializa y configura el contexto SSL"""
        try:
            # Verificar que los archivos existen
            if not Path(self.certfile).exists():
                raise FileNotFoundError(f"Certificado no encontrado: {self.certfile}")
            if not Path(self.keyfile).exists():
                raise FileNotFoundError(f"Clave no encontrada: {self.keyfile}")
                
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            self.logger.info("Contexto SSL configurado correctamente")
            return context
            
        except Exception as e:
            self.logger.error(f"Error configurando SSL: {e}")
            raise
    
    def broadcast_message(self, message: ChatMessage, exclude_client: Optional[ClientConnection] = None):
        """
        Envía un mensaje a todos los clientes conectados
        """
        disconnected_clients = []
        
        for client_conn in self.clients.values():
            try:
                if client_conn != exclude_client and client_conn.authenticated:
                    client_conn.socket.send(message.to_json().encode('utf-8'))
                    client_conn.last_activity = time.time()
                    
            except (ssl.SSLError, BrokenPipeError, OSError):
                disconnected_clients.append(client_conn)
                self.logger.warning(f"Cliente {client_conn.username} desconectado durante broadcast")
        
        # Limpiar clientes desconectados
        for client in disconnected_clients:
            self.remove_client(client)
    
    def send_to_client(self, client: ClientConnection, message: ChatMessage):
        """Envía un mensaje a un cliente específico"""
        try:
            client.socket.send(message.to_json().encode('utf-8'))
            client.last_activity = time.time()
        except (ssl.SSLError, BrokenPipeError, OSError):
            self.logger.warning(f"Error enviando mensaje a {client.username}")
            self.remove_client(client)
    
    def handle_client_authentication(self, client_conn: ClientConnection) -> bool:
        """Maneja la autenticación del cliente"""
        try:
            # Solicitar nombre de usuario
            auth_message = SystemMessage("Por favor, ingresa tu nombre de usuario:", "info")
            self.send_to_client(client_conn, auth_message)
            
            # Recibir respuesta
            data = client_conn.socket.recv(1024).decode('utf-8')
            if not ProtocolValidator.validate_message(data):
                error_msg = ErrorMessage("INVALID_MESSAGE", "Mensaje de autenticación inválido")
                self.send_to_client(client_conn, error_msg)
                return False
            
            message = ChatMessage.from_json(data)
            username = message.sender.strip()
            
            # Validar nombre de usuario
            if not username:
                error_msg = ErrorMessage("INVALID_USERNAME", "El nombre de usuario no puede estar vacío")
                self.send_to_client(client_conn, error_msg)
                return False
            
            if username in self.usernames:
                error_msg = ErrorMessage("USERNAME_TAKEN", f"El nombre '{username}' ya está en uso")
                self.send_to_client(client_conn, error_msg)
                return False
            
            # Autenticación exitosa
            client_conn.username = username
            client_conn.authenticated = True
            self.usernames.add(username)
            
            # Notificar a todos
            welcome_msg = SystemMessage(f"Usuario {username} se ha unido al chat!", "info")
            self.broadcast_message(welcome_msg)
            
            self.logger.info(f"Cliente autenticado: {username} desde {client_conn.address}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error en autenticación: {e}")
            return False
    
    def handle_client_message(self, client_conn: ClientConnection, message_data: str):
        """Procesa un mensaje recibido del cliente"""
        try:
            if not ProtocolValidator.validate_message(message_data):
                error_msg = ErrorMessage("INVALID_MESSAGE", "Mensaje con formato inválido")
                self.send_to_client(client_conn, error_msg)
                return
            
            message = ChatMessage.from_json(message_data)
            
            # Procesar según el tipo de mensaje
            if message.type == MessageType.CHAT:
                self.handle_chat_message(client_conn, message)
            elif message.type == MessageType.COMMAND:
                self.handle_command_message(client_conn, message)
            else:
                self.logger.warning(f"Tipo de mensaje no soportado: {message.type}")
                
        except Exception as e:
            self.logger.error(f"Error procesando mensaje: {e}")
            error_msg = ErrorMessage("PROCESSING_ERROR", "Error procesando el mensaje")
            self.send_to_client(client_conn, error_msg)
    
    def handle_chat_message(self, client_conn: ClientConnection, message: ChatMessage):
        """Maneja mensajes de chat normales"""
        if not client_conn.authenticated:
            error_msg = ErrorMessage("NOT_AUTHENTICATED", "Debes autenticarte primero")
            self.send_to_client(client_conn, error_msg)
            return
        
        # Sanitizar contenido
        sanitized_content = ProtocolValidator.sanitize_content(message.content)
        
        # Crear mensaje para broadcast
        chat_msg = MessageFactory.create_chat_message(
            client_conn.username, 
            sanitized_content,
            message.metadata.get('room', 'general') if message.metadata else 'general'
        )
        
        # Enviar a todos
        self.broadcast_message(chat_msg, exclude_client=client_conn)
        
        # También enviar confirmación al remitente
        self.send_to_client(client_conn, chat_msg)
        
        # Log sin emojis para Windows
        self.logger.info(f"Mensaje de {client_conn.username}: {sanitized_content}")
    
    def handle_command_message(self, client_conn: ClientConnection, message: ChatMessage):
        """Maneja mensajes de comando"""
        if not client_conn.authenticated:
            error_msg = ErrorMessage("NOT_AUTHENTICATED", "Debes autenticarte primero")
            self.send_to_client(client_conn, error_msg)
            return
        
        command = message.content
        
        if command == CommandType.LIST_USERS.value:
            users_list = ", ".join(self.usernames)
            # Mensaje sin emojis para Windows
            response = SystemMessage(f"Usuarios conectados: {users_list}", "info")
            self.send_to_client(client_conn, response)
            
        elif command == CommandType.QUIT.value:
            self.remove_client(client_conn)
            
        else:
            error_msg = ErrorMessage("UNKNOWN_COMMAND", f"Comando '{command}' no reconocido")
            self.send_to_client(client_conn, error_msg)
    
    def remove_client(self, client_conn: ClientConnection):
        """Elimina un cliente de forma segura"""
        if client_conn.username in self.usernames:
            self.usernames.remove(client_conn.username)
        
        if client_conn.socket in self.clients:
            del self.clients[client_conn.socket]
        
        # Notificar desconexión
        if client_conn.authenticated:
            leave_msg = SystemMessage(f"Usuario {client_conn.username} ha abandonado el chat", "info")
            self.broadcast_message(leave_msg)
        
        # Cerrar conexión
        try:
            client_conn.socket.close()
        except:
            pass
        
        # Log sin emojis para Windows
        self.logger.info(f"Cliente desconectado: {client_conn.username}")
    
    def client_handler(self, client_socket: ssl.SSLSocket, address: tuple):
        """Maneja la comunicación con un cliente individual"""
        client_conn = ClientConnection(client_socket, address)
        self.clients[client_socket] = client_conn
        
        # Log sin emojis para Windows
        self.logger.info(f"Nueva conexión desde {address}")
        
        try:
            # Proceso de autenticación
            if not self.handle_client_authentication(client_conn):
                self.remove_client(client_conn)
                return
            
            # Loop principal de mensajes
            while self.running and client_conn.connected:
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break  # Cliente desconectado
                    
                    self.handle_client_message(client_conn, data)
                    
                except socket.timeout:
                    continue
                except (ssl.SSLError, ConnectionResetError, BrokenPipeError):
                    break
                    
        except Exception as e:
            self.logger.error(f"Error en client_handler: {e}")
        finally:
            self.remove_client(client_conn)
    
    def start(self):
        """Inicia el servidor"""
        try:
            # Crear directorio de logs si no existe
            Path("logs").mkdir(exist_ok=True)
            
            # Crear socket base
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.listen(5)
            
            # Configurar SSL
            ssl_context = self.initialize_ssl_context()
            self.server_socket = ssl_context.wrap_socket(sock, server_side=True)
            
            self.running = True
            
            self.logger.info(f"Servidor Secure Chat iniciado en {self.host}:{self.port}")
            self.logger.info("Esperando conexiones seguras...")
            
            # Aceptar conexiones
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    
                    # Crear hilo para el cliente
                    client_thread = threading.Thread(
                        target=self.client_handler,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except ssl.SSLError as e:
                    self.logger.error(f"Error SSL aceptando conexión: {e}")
                except OSError as e:
                    if self.running:
                        self.logger.error(f"Error aceptando conexión: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error iniciando servidor: {e}")
            raise
    
    def stop(self):
        """Detiene el servidor de forma segura"""
        self.logger.info("Deteniendo servidor...")
        self.running = False
        
        # Cerrar todas las conexiones de clientes
        for client_conn in list(self.clients.values()):
            self.remove_client(client_conn)
        
        # Cerrar socket del servidor
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        self.logger.info("Servidor detenido correctamente")


# Ejemplo de uso
if __name__ == "__main__":
    server = SecureChatServer(
        host='localhost',
        port=9999,
        certfile='certificates/server.crt',  # Ruta desde la raíz
        keyfile='certificates/server.key'
    )
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServidor interrumpido por el usuario")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        server.stop()
import socket
import threading
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Set
from cryptography.fernet import Fernet

try:
    from protocol import (
        MessageType, CommandType, ChatMessage, SystemMessage,
        ErrorMessage, MessageFactory, ProtocolValidator
    )
except ImportError:
    from .protocol import (
        MessageType, CommandType, ChatMessage, SystemMessage,
        ErrorMessage, MessageFactory, ProtocolValidator
    )


class ClientConnection:
    """Representa una conexión de cliente individual"""
    def __init__(self, client_socket: socket.socket, address: tuple, username: str = "", fernet: Fernet = None):
        self.socket = client_socket
        self.address = address
        self.username = username
        self.connected = True
        self.authenticated = False
        self.last_activity = time.time()
        self.fernet = fernet


class ChatRoom:
    """Representa una sala de chat"""
    def __init__(self, name: str):
        self.name = name
        self.clients: Set[ClientConnection] = set()
        self.created_at = time.time()


class SecureChatServer:
    """Servidor principal de chat seguro con cifrado simétrico"""
    
    def __init__(self, host: str = 'localhost', port: int = 9999, keyfile: str = "certificates/symmetric.key"):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.clients: Dict[socket.socket, ClientConnection] = {}
        self.rooms: Dict[str, ChatRoom] = {"general": ChatRoom("general")}
        self.usernames: Set[str] = set()
        self.keyfile = keyfile
        self.fernet = self.load_or_generate_key()
        self.setup_logging()

    def setup_logging(self):
        Path("logs").mkdir(exist_ok=True)
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('logs/secure_chat.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('SecureChatServer')

    def load_or_generate_key(self) -> Fernet:
        Path("certificates").mkdir(exist_ok=True)
        if Path(self.keyfile).exists():
            with open(self.keyfile, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.keyfile, "wb") as f:
                f.write(key)
        return Fernet(key)

    def broadcast_message(self, message: ChatMessage, exclude_client: Optional[ClientConnection] = None):
        disconnected_clients = []
        for client_conn in self.clients.values():
            try:
                if client_conn != exclude_client and client_conn.authenticated:
                    encrypted = client_conn.fernet.encrypt(message.to_json().encode())
                    client_conn.socket.send(encrypted)
                    client_conn.last_activity = time.time()
            except (ConnectionResetError, BrokenPipeError, OSError):
                disconnected_clients.append(client_conn)
                self.logger.warning(f"Cliente {client_conn.username} desconectado durante broadcast")
        for client in disconnected_clients:
            self.remove_client(client)

    def send_to_client(self, client: ClientConnection, message: ChatMessage):
        try:
            encrypted = client.fernet.encrypt(message.to_json().encode())
            client.socket.send(encrypted)
            client.last_activity = time.time()
        except (ConnectionResetError, BrokenPipeError, OSError):
            self.logger.warning(f"Error enviando mensaje a {client.username}")
            self.remove_client(client)

    def handle_client_authentication(self, client_conn: ClientConnection) -> bool:
        try:
            auth_msg = SystemMessage("Por favor, ingresa tu nombre de usuario:", "info")
            self.send_to_client(client_conn, auth_msg)
            data = client_conn.socket.recv(2048)
            decrypted = client_conn.fernet.decrypt(data).decode('utf-8')
            if not ProtocolValidator.validate_message(decrypted):
                error_msg = ErrorMessage("INVALID_MESSAGE", "Mensaje de autenticación inválido")
                self.send_to_client(client_conn, error_msg)
                return False
            message = ChatMessage.from_json(decrypted)
            username = message.sender.strip()
            if not username:
                self.send_to_client(client_conn, ErrorMessage("INVALID_USERNAME", "Nombre vacío"))
                return False
            if username in self.usernames:
                self.send_to_client(client_conn, ErrorMessage("USERNAME_TAKEN", f"'{username}' en uso"))
                return False
            client_conn.username = username
            client_conn.authenticated = True
            self.usernames.add(username)
            welcome_msg = SystemMessage(f"Usuario {username} se ha unido al chat!", "info")
            self.broadcast_message(welcome_msg)
            self.logger.info(f"Cliente autenticado: {username} desde {client_conn.address}")
            return True
        except Exception as e:
            self.logger.error(f"Error en autenticación: {e}")
            return False

    def handle_client_message(self, client_conn: ClientConnection, message_data: bytes):
        try:
            decrypted = client_conn.fernet.decrypt(message_data).decode('utf-8')
            if not ProtocolValidator.validate_message(decrypted):
                self.send_to_client(client_conn, ErrorMessage("INVALID_MESSAGE", "Mensaje inválido"))
                return
            message = ChatMessage.from_json(decrypted)
            if message.type == MessageType.CHAT:
                self.handle_chat_message(client_conn, message)
            elif message.type == MessageType.COMMAND:
                self.handle_command_message(client_conn, message)
        except Exception as e:
            self.logger.error(f"Error procesando mensaje: {e}")
            self.send_to_client(client_conn, ErrorMessage("PROCESSING_ERROR", "Error procesando mensaje"))

    def handle_chat_message(self, client_conn: ClientConnection, message: ChatMessage):
        if not client_conn.authenticated:
            self.send_to_client(client_conn, ErrorMessage("NOT_AUTHENTICATED", "Debes autenticarte"))
            return
        sanitized_content = ProtocolValidator.sanitize_content(message.content)
        chat_msg = MessageFactory.create_chat_message(
            client_conn.username,
            sanitized_content,
            message.metadata.get('room', 'general') if message.metadata else 'general'
        )
        self.broadcast_message(chat_msg, exclude_client=client_conn)
        self.send_to_client(client_conn, chat_msg)
        self.logger.info(f"Mensaje de {client_conn.username}: {sanitized_content}")

    def handle_command_message(self, client_conn: ClientConnection, message: ChatMessage):
        if not client_conn.authenticated:
            self.send_to_client(client_conn, ErrorMessage("NOT_AUTHENTICATED", "Debes autenticarte"))
            return
        command = message.content
        if command == CommandType.LIST_USERS.value:
            users_list = ", ".join(self.usernames)
            self.send_to_client(client_conn, SystemMessage(f"Usuarios conectados: {users_list}", "info"))
        elif command == CommandType.QUIT.value:
            self.remove_client(client_conn)
        else:
            self.send_to_client(client_conn, ErrorMessage("UNKNOWN_COMMAND", f"'{command}' no reconocido"))

    def remove_client(self, client_conn: ClientConnection):
        if client_conn.username in self.usernames:
            self.usernames.remove(client_conn.username)
        if client_conn.socket in self.clients:
            del self.clients[client_conn.socket]
        if client_conn.authenticated:
            leave_msg = SystemMessage(f"Usuario {client_conn.username} ha abandonado el chat", "info")
            self.broadcast_message(leave_msg)
        try:
            client_conn.socket.close()
        except:
            pass
        self.logger.info(f"Cliente desconectado: {client_conn.username}")

    def client_handler(self, client_socket: socket.socket, address: tuple):
        client_conn = ClientConnection(client_socket, address, fernet=self.fernet)
        self.clients[client_socket] = client_conn
        self.logger.info(f"Nueva conexión desde {address}")
        try:
            if not self.handle_client_authentication(client_conn):
                self.remove_client(client_conn)
                return
            while self.running and client_conn.connected:
                try:
                    data = client_socket.recv(2048)
                    if not data:
                        break
                    self.handle_client_message(client_conn, data)
                except socket.timeout:
                    continue
                except (ConnectionResetError, BrokenPipeError):
                    break
        except Exception as e:
            self.logger.error(f"Error en client_handler: {e}")
        finally:
            self.remove_client(client_conn)

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        self.logger.info(f"Servidor Secure Chat iniciado en {self.host}:{self.port}")
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(target=self.client_handler, args=(client_socket, address), daemon=True)
                client_thread.start()
            except OSError:
                break

    def stop(self):
        self.running = False
        for client in list(self.clients.values()):
            self.remove_client(client)
        if self.server_socket:
            self.server_socket.close()
        self.logger.info("Servidor detenido correctamente")


if __name__ == "__main__":
    server = SecureChatServer(host='localhost', port=9999)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServidor interrumpido por el usuario")
    finally:
        server.stop()

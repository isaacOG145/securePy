import socket
import threading
import time
from typing import Optional, Callable
from cryptography.fernet import Fernet
from pathlib import Path

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


class SecureChatClient:
    def __init__(self, host='localhost', port=9999, username: str = None, keyfile="certificates/symmetric.key"):
        self.host = host
        self.port = port
        self.username = username
        self.connected = False
        self.authenticated = False
        self.socket: Optional[socket.socket] = None
        self.fernet = self.load_key(keyfile)
        self.on_message_received: Optional[Callable] = None
        self.on_connection_changed: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.receive_thread: Optional[threading.Thread] = None

    def load_key(self, keyfile: str) -> Fernet:
        Path("certificates").mkdir(exist_ok=True)
        if not Path(keyfile).exists():
            raise FileNotFoundError(f"Key file not found: {keyfile}")
        with open(keyfile, "rb") as f:
            key = f.read()
        return Fernet(key)

    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receive_thread.start()
            return True
        except Exception as e:
            self.connected = False
            if self.on_error:
                self.on_error(f"Error conectando al servidor: {e}")
            return False

    def _receive_messages(self):
        while self.connected:
            try:
                data = self.socket.recv(2048)
                if not data:
                    self.connected = False
                    break
                decrypted = self.fernet.decrypt(data).decode('utf-8')
                message = ChatMessage.from_json(decrypted) if ProtocolValidator.validate_message(decrypted) else SystemMessage(decrypted, "info")
                if self.on_message_received:
                    self.on_message_received(message)
            except Exception as e:
                if self.on_error:
                    self.on_error(f"Error recibiendo mensaje: {e}")
                self.connected = False
                break

    import time  # al inicio del archivo

    def authenticate(self, username: str) -> bool:
        if not self.connected:
            return False
        try:
            self.username = username
            auth_msg = ChatMessage(
                sender=username,
                content=username,
                type=MessageType.CHAT,
                timestamp=int(time.time())  # <-- aquí agregamos timestamp
            )
            encrypted = self.fernet.encrypt(auth_msg.to_json().encode())
            self.socket.send(encrypted)
            self.authenticated = True
            return True
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error durante autenticación: {e}")
            return False

    def send_message(self, content: str):
        if not self.connected or not self.authenticated:
            return
        try:
            message = MessageFactory.create_chat_message(self.username, content)
            encrypted = self.fernet.encrypt(message.to_json().encode())
            self.socket.send(encrypted)
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error enviando mensaje: {e}")

    def send_command(self, command: str):
        if not self.connected or not self.authenticated:
            return
        try:
            message = ChatMessage(sender=self.username, content=command, type=MessageType.COMMAND)
            encrypted = self.fernet.encrypt(message.to_json().encode())
            self.socket.send(encrypted)
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error enviando comando: {e}")

    def disconnect(self):
        self.connected = False
        try:
            if self.socket:
                self.socket.close()
        except:
            pass
        if self.on_connection_changed:
            self.on_connection_changed(False)


# Cliente de consola para prueba
class ConsoleChatClient(SecureChatClient):
    def __init__(self, host='localhost', port=9999):
        super().__init__(host, port)
        self.on_message_received = self.print_message
        self.on_error = self.print_error
        self.on_connection_changed = self.print_connection_status

    def print_message(self, message):
        if isinstance(message, ChatMessage):
            print(f"[{message.sender}] {message.content}")
        elif isinstance(message, SystemMessage):
            print(f"[SYSTEM] {message.content}")
        elif isinstance(message, ErrorMessage):
            print(f"[ERROR] {message.content}")

    def print_error(self, msg):
        print(f"[ERROR] {msg}")

    def print_connection_status(self, status):
        print(f"[INFO] Conectado: {status}")


if __name__ == "__main__":
    client = ConsoleChatClient()
    if client.connect():
        username = input("Ingresa tu nombre de usuario: ")
        if client.authenticate(username):
            print("Conectado y autenticado! Escribe tus mensajes o /quit para salir.")
            while client.connected:
                text = input()
                if text.strip() == "/quit":
                    client.send_command("/quit")
                    client.disconnect()
                    break
                elif text.strip() == "/users":
                    client.send_command("/users")
                else:
                    client.send_message(text)

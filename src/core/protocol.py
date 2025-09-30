"""
Protocolo de comunicación para Secure Chat
Define la estructura de mensajes entre cliente y servidor
"""

import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Union
from enum import Enum


class MessageType(Enum):
    """Tipos de mensajes soportados por el protocolo"""
    AUTH = "auth"           # Autenticación de usuario
    CHAT = "chat"           # Mensaje de chat normal
    SYSTEM = "system"       # Mensaje del sistema
    COMMAND = "command"     # Comando especial
    ERROR = "error"         # Mensaje de error
    STATUS = "status"       # Estado de conexión


class CommandType(Enum):
    """Comandos especiales soportados"""
    JOIN = "join"           # Unirse al chat
    LEAVE = "leave"         # Salir del chat
    LIST_USERS = "list_users"  # Listar usuarios
    WHISPER = "whisper"     # Mensaje privado
    QUIT = "quit"           # Salir de la aplicación


@dataclass
class ChatMessage:
    """
    Estructura base para todos los mensajes del chat
    """
    type: MessageType
    timestamp: float
    sender: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        """Convierte el mensaje a JSON string"""
        data = asdict(self)
        data['type'] = self.type.value  # Convertir Enum a string
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ChatMessage':
        """Crea un ChatMessage desde JSON string"""
        data = json.loads(json_str)
        data['type'] = MessageType(data['type'])  # Convertir string a Enum
        return cls(**data)


@dataclass
class AuthMessage(ChatMessage):
    """Mensaje de autenticación"""
    def __init__(self, username: str, password: Optional[str] = None):
        super().__init__(
            type=MessageType.AUTH,
            timestamp=time.time(),
            sender=username,
            content="authentication",
            metadata={"password": password} if password else None
        )


@dataclass  
class ChatTextMessage(ChatMessage):
    """Mensaje de texto normal del chat"""
    def __init__(self, sender: str, content: str, room: str = "general"):
        super().__init__(
            type=MessageType.CHAT,
            timestamp=time.time(),
            sender=sender,
            content=content,
            metadata={"room": room}
        )


@dataclass
class SystemMessage(ChatMessage):
    """Mensaje del sistema (notificaciones, etc.)"""
    def __init__(self, content: str, level: str = "info"):
        super().__init__(
            type=MessageType.SYSTEM,
            timestamp=time.time(),
            sender="system",
            content=content,
            metadata={"level": level}  # info, warning, error, success
        )


@dataclass
class CommandMessage(ChatMessage):
    """Mensaje de comando especial"""
    def __init__(self, sender: str, command: CommandType, params: Optional[Dict] = None):
        super().__init__(
            type=MessageType.COMMAND,
            timestamp=time.time(),
            sender=sender,
            content=command.value,
            metadata={"params": params} if params else None
        )


@dataclass
class ErrorMessage(ChatMessage):
    """Mensaje de error"""
    def __init__(self, error_code: str, error_message: str, details: Optional[Dict] = None):
        super().__init__(
            type=MessageType.ERROR,
            timestamp=time.time(),
            sender="system",
            content=error_message,
            metadata={"error_code": error_code, "details": details}
        )


class MessageFactory:
    """Factory para crear mensajes de forma sencilla"""
    
    @staticmethod
    def create_chat_message(sender: str, content: str, room: str = "general") -> ChatTextMessage:
        """Crea un mensaje de chat normal"""
        return ChatTextMessage(sender, content, room)
    
    @staticmethod
    def create_system_message(content: str, level: str = "info") -> SystemMessage:
        """Crea un mensaje del sistema"""
        return SystemMessage(content, level)
    
    @staticmethod
    def create_auth_message(username: str) -> AuthMessage:
        """Crea un mensaje de autenticación"""
        return AuthMessage(username)
    
    @staticmethod
    def create_command_message(sender: str, command: CommandType, **params) -> CommandMessage:
        """Crea un mensaje de comando"""
        return CommandMessage(sender, command, params)
    
    @staticmethod
    def create_error_message(error_code: str, error_message: str, **details) -> ErrorMessage:
        """Crea un mensaje de error"""
        return ErrorMessage(error_code, error_message, details)


class ProtocolValidator:
    """Validador del protocolo de mensajes"""
    
    @staticmethod
    def validate_message(json_str: str) -> bool:
        """Valida que un mensaje JSON tenga la estructura correcta"""
        try:
            data = json.loads(json_str)
            required_fields = ['type', 'timestamp', 'sender', 'content']
            
            # Verificar campos requeridos
            if not all(field in data for field in required_fields):
                return False
            
            # Verificar que el tipo sea válido
            if data['type'] not in [t.value for t in MessageType]:
                return False
            
            # Verificar tipos de datos
            if not isinstance(data['timestamp'], (int, float)):
                return False
            if not isinstance(data['sender'], str):
                return False
            if not isinstance(data['content'], str):
                return False
            
            return True
            
        except (json.JSONDecodeError, KeyError, TypeError):
            return False
    
    @staticmethod
    def sanitize_content(content: str) -> str:
        """Limpia y sanitiza el contenido del mensaje"""
        sanitized = ''.join(
            char for char in content 
            if char.isprintable() or char in ['\n', '\t']
        )
        return sanitized[:516]  


# Ejemplos de uso
if __name__ == "__main__":
    # Crear mensajes de ejemplo
    chat_msg = MessageFactory.create_chat_message("usuario1", "¡Hola mundo!")
    system_msg = MessageFactory.create_system_message("Usuario conectado", "info")
    command_msg = MessageFactory.create_command_message("usuario1", CommandType.LIST_USERS)
    
    print("=== Ejemplos del Protocolo ===")
    print("Chat Message:", chat_msg.to_json())
    print("System Message:", system_msg.to_json()) 
    print("Command Message:", command_msg.to_json())
    
    # Validar mensajes
    print("\n=== Validación ===")
    print("Chat válido:", ProtocolValidator.validate_message(chat_msg.to_json()))
    print("JSON inválido:", ProtocolValidator.validate_message("{}"))
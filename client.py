import socket
import threading
import time

class ClienteChat:
    def __init__(self, host='localhost', puerto=9999):
        self.host = host
        self.puerto = puerto
        self.socket_cliente = None
        self.nombre_usuario = ""
        self.conectado = False
        
    def conectar_servidor(self):
        """Establece conexión con el servidor"""
        try:
            self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_cliente.connect((self.host, self.puerto))
            self.conectado = True
            print(f"✅ Conectado al servidor {self.host}:{self.puerto}")
            return True
        except Exception as e:
            print(f"❌ No se pudo conectar al servidor: {e}")
            return False

    def recibir_mensajes(self):
        """Hilo para recibir mensajes del servidor"""
        while self.conectado:
            try:
                mensaje = self.socket_cliente.recv(1024).decode('utf-8')
                if mensaje:
                    print(f"\n{mensaje}")
                    print("Tú: ", end="", flush=True)  # Mantener prompt visible
            except:
                print("\n❌ Conexión con el servidor perdida")
                self.conectado = False
                break

    def enviar_mensajes(self):
        """Hilo para enviar mensajes al servidor"""
        # Primero obtener nombre de usuario
        try:
            mensaje_servidor = self.socket_cliente.recv(1024).decode('utf-8')
            if mensaje_servidor == "NICK":
                self.nombre_usuario = input("Ingresa tu nombre de usuario: ")
                self.socket_cliente.send(self.nombre_usuario.encode('utf-8'))
        except:
            print("Error al configurar nombre de usuario")
            return

        print("\n💬 ¡Bienvenido al chat! Escribe tus mensajes (/'quit' para salir)")
        
        while self.conectado:
            try:
                mensaje = input("Tú: ")
                
                if mensaje.lower() == '/quit':
                    self.socket_cliente.send('/quit'.encode('utf-8'))
                    break
                elif mensaje.strip():
                    self.socket_cliente.send(mensaje.encode('utf-8'))
                    
            except KeyboardInterrupt:
                print("\nSaliendo...")
                self.socket_cliente.send('/quit'.encode('utf-8'))
                break
            except Exception as e:
                print(f"Error al enviar mensaje: {e}")
                break

    def ejecutar(self):
        """Método principal del cliente"""
        if not self.conectar_servidor():
            return
        
        try:
            # Hilo para recibir mensajes
            hilo_recepcion = threading.Thread(target=self.recibir_mensajes)
            hilo_recepcion.daemon = True
            hilo_recepcion.start()
            
            # Hilo principal para enviar mensajes
            self.enviar_mensajes()
            
        except KeyboardInterrupt:
            print("\n👋 Saliendo del chat...")
        finally:
            self.conectado = False
            if self.socket_cliente:
                self.socket_cliente.close()
            print("✅ Desconectado del servidor")

if __name__ == "__main__":
    cliente = ClienteChat(host='localhost', puerto=9999)
    cliente.ejecutar()
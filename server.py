import socket
import threading
import time

class ServidorChat:
    def __init__(self, host='localhost', puerto=9999):
        """
        Inicializa el servidor de chat
        
        Args:
            host (str): Dirección IP del servidor
            puerto (int): Puerto donde escuchará el servidor
        """
        self.host = host
        self.puerto = puerto
        self.clientes_conectados = []  # Lista de sockets de clientes conectados
        self.nombres_usuarios = {}     # Diccionario: socket -> nombre de usuario
        self.socket_servidor = None
        self.inicializar_servidor()

    def inicializar_servidor(self):
        """Crea y configura el socket del servidor"""
        try:
            # Crear socket TCP
            self.socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Permitir reutilizar la dirección (útil para reinicios rápidos)
            self.socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Vincular socket a la dirección y puerto
            self.socket_servidor.bind((self.host, self.puerto))
            
            # Escuchar conexiones entrantes (máximo 5 en cola)
            self.socket_servidor.listen(5)
            
            print(f"🚀 Servidor de chat activo en {self.host}:{self.puerto}")
            print("📍 Esperando conexiones de clientes...")
            print("📍 Presiona Ctrl+C para detener el servidor\n")
            
        except Exception as e:
            print(f"❌ Error al iniciar el servidor: {e}")
            exit(1)

    def broadcast(self, mensaje, cliente_emisor=None):
        """
        Envía un mensaje a todos los clientes conectados excepto al emisor
        
        Args:
            mensaje (str): Mensaje a enviar
            cliente_emisor (socket): Cliente que envió el mensaje (opcional)
        """
        clientes_a_eliminar = []
        
        for cliente in self.clientes_conectados[:]:  # Copia de la lista para iterar seguro
            try:
                # No reenviar al cliente que envió el mensaje (si se especifica)
                if cliente != cliente_emisor:
                    cliente.send(mensaje.encode('utf-8'))
            except:
                # Si falla el envío, marcar cliente para eliminar
                clientes_a_eliminar.append(cliente)
        
        # Eliminar clientes desconectados
        for cliente in clientes_a_eliminar:
            self.eliminar_cliente(cliente)

    def manejar_cliente(self, cliente, direccion):
        """
        Maneja la comunicación con un cliente específico en un hilo separado
        
        Args:
            cliente (socket): Socket del cliente
            direccion (tuple): Tupla (ip, puerto) del cliente
        """
        nombre_usuario = "Anónimo"
        
        try:
            # Solicitar nombre de usuario al cliente
            cliente.send("NICK".encode('utf-8'))
            nombre_usuario = cliente.recv(1024).decode('utf-8').strip()
            
            # Validar nombre de usuario
            if not nombre_usuario:
                nombre_usuario = f"Usuario_{direccion[1]}"
            
            # Registrar cliente
            self.nombres_usuarios[cliente] = nombre_usuario
            self.clientes_conectados.append(cliente)
            
            # Notificar entrada al chat
            mensaje_bienvenida = f"🌟 {nombre_usuario} se ha unido al chat!"
            print(mensaje_bienvenida)
            self.broadcast(mensaje_bienvenida, cliente)
            
            # Enviar mensaje de bienvenida personalizado
            cliente.send(f"Bienvenido al chat, {nombre_usuario}!".encode('utf-8'))
            cliente.send("Escribe '/quit' para salir".encode('utf-8'))
            
            # Loop principal de mensajes del cliente
            while True:
                mensaje = cliente.recv(1024).decode('utf-8').strip()
                
                if not mensaje:
                    continue
                
                # Comando para salir
                if mensaje.lower() == '/quit':
                    break
                
                # Comando para listar usuarios
                elif mensaje.lower() == '/users':
                    usuarios = ", ".join(self.nombres_usuarios.values())
                    cliente.send(f"👥 Usuarios conectados: {usuarios}".encode('utf-8'))
                
                # Mensaje normal
                else:
                    mensaje_completo = f"{nombre_usuario}: {mensaje}"
                    print(f"[{time.strftime('%H:%M:%S')}] {mensaje_completo}")
                    self.broadcast(mensaje_completo, cliente)
                    
        except ConnectionResetError:
            print(f"⚠️  {nombre_usuario} se desconectó abruptamente")
        except Exception as e:
            print(f"❌ Error con cliente {nombre_usuario}: {e}")
        finally:
            self.eliminar_cliente(cliente)

    def eliminar_cliente(self, cliente):
        """
        Elimina un cliente de las listas y cierra su conexión
        
        Args:
            cliente (socket): Socket del cliente a eliminar
        """
        if cliente in self.clientes_conectados:
            # Obtener nombre del usuario
            nombre_usuario = self.nombres_usuarios.get(cliente, "Usuario desconocido")
            
            # Remover de las listas
            self.clientes_conectados.remove(cliente)
            if cliente in self.nombres_usuarios:
                del self.nombres_usuarios[cliente]
            
            # Notificar desconexión
            mensaje_desconexion = f"👋 {nombre_usuario} ha abandonado el chat"
            print(mensaje_desconexion)
            self.broadcast(mensaje_desconexion)
            
            # Cerrar conexión
            try:
                cliente.close()
            except:
                pass

    def mostrar_estado(self):
        """Muestra el estado actual del servidor"""
        print(f"\n📊 Estado del servidor:")
        print(f"   👥 Usuarios conectados: {len(self.clientes_conectados)}")
        if self.nombres_usuarios:
            print(f"   📝 Usuarios: {', '.join(self.nombres_usuarios.values())}")
        print()

    def ejecutar(self):
        """Loop principal que acepta nuevas conexiones indefinidamente"""
        print("Iniciando servidor...")
        
        try:
            while True:
                try:
                    # Esperar nueva conexión (esto bloquea hasta que llegue una)
                    cliente, direccion = self.socket_servidor.accept()
                    print(f"✅ Nueva conexión desde {direccion[0]}:{direccion[1]}")
                    
                    # Crear hilo para manejar el nuevo cliente
                    hilo_cliente = threading.Thread(
                        target=self.manejar_cliente, 
                        args=(cliente, direccion)
                    )
                    hilo_cliente.daemon = True  # Hilo se cierra cuando el main termina
                    hilo_cliente.start()
                    
                    # Mostrar estado cada 5 conexiones
                    if len(self.clientes_conectados) % 5 == 0:
                        self.mostrar_estado()
                        
                except KeyboardInterrupt:
                    print("\n🛑 Deteniendo servidor...")
                    break
                except Exception as e:
                    print(f"❌ Error aceptando conexión: {e}")
                    time.sleep(1)  # Esperar antes de reintentar
                    
        except KeyboardInterrupt:
            print("\n🛑 Servidor interrumpido por el usuario")
        finally:
            self.cerrar_servidor()

    def cerrar_servidor(self):
        """Cierra todas las conexiones y el socket del servidor"""
        print("\n🔒 Cerrando todas las conexiones...")
        
        # Cerrar todos los clientes
        for cliente in self.clientes_conectados[:]:
            self.eliminar_cliente(cliente)
        
        # Cerrar socket del servidor
        if self.socket_servidor:
            self.socket_servidor.close()
            print("✅ Servidor cerrado correctamente")

if __name__ == "__main__":
    # Crear y ejecutar servidor
    servidor = ServidorChat(host='localhost', puerto=9999)
    
    try:
        servidor.ejecutar()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
    finally:
        servidor.cerrar_servidor()
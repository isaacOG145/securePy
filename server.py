import socket
import threading
import time
import ssl # Importamos el módulo SSL

class ServidorChat:
    def __init__(self, host='localhost', puerto=9999):
        """
        Inicializa el servidor de chat
        """
        self.host = host
        self.puerto = puerto
        self.clientes_conectados = []  
        self.nombres_usuarios = {}     
        self.socket_servidor = None
        self.certfile = 'cert.pem' # Archivo de certificado
        self.keyfile = 'key.pem'   # Archivo de clave privada
        self.inicializar_servidor()

    def inicializar_servidor(self):
        """Crea y configura el socket del servidor (con SSL)"""
        try:
            # 1. Crear socket TCP normal
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.puerto))
            sock.listen(5)
            
            # 2. Crear contexto SSL/TLS
            # Usamos Purpose.CLIENT_AUTH porque el servidor requiere autenticar al cliente (aunque no lo forcemos)
            self.contexto_ssl = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.contexto_ssl.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
            
            # 3. CORRECCIÓN: Envolver el socket en el contexto SSL usando server_side=True
            self.socket_servidor = self.contexto_ssl.wrap_socket(sock, server_side=True)

            print(f"🚀 Servidor de chat ACTIVO y SEGURO (SSL) en {self.host}:{self.puerto}")
            print("📍 Esperando conexiones SEGURAS de clientes...")
            print("📍 Presiona Ctrl+C para detener el servidor\n")
            
        except FileNotFoundError:
            print(f"❌ Error: Archivos SSL/TLS '{self.certfile}' o '{self.keyfile}' no encontrados.")
            print("❌ El servidor no puede iniciar de forma segura. Asegúrate de generarlos con OpenSSL.")
            exit(1)
        except Exception as e:
            print(f"❌ Error al iniciar el servidor: {e}")
            exit(1)

    def broadcast(self, mensaje, cliente_emisor=None):
        """Envía un mensaje a todos los clientes conectados excepto al emisor"""
        clientes_a_eliminar = []
        for cliente in self.clientes_conectados[:]:
            try:
                if cliente != cliente_emisor:
                    cliente.send(mensaje.encode('utf-8'))
            except:
                clientes_a_eliminar.append(cliente)
        
        for cliente in clientes_a_eliminar:
            self.eliminar_cliente(cliente)

    def manejar_cliente(self, cliente_envuelto, direccion):
        """Maneja la comunicación con un cliente específico en un hilo separado"""
        nombre_usuario = "Anónimo"
        
        try:
            # Lógica de NICK (ahora usando el socket envuelto)
            cliente_envuelto.send("NICK".encode('utf-8'))
            nombre_usuario = cliente_envuelto.recv(1024).decode('utf-8').strip()
            
            if not nombre_usuario:
                nombre_usuario = f"Usuario_{direccion[1]}"
            
            self.nombres_usuarios[cliente_envuelto] = nombre_usuario
            self.clientes_conectados.append(cliente_envuelto)
            
            mensaje_bienvenida = f"🌟 {nombre_usuario} se ha unido al chat!"
            print(mensaje_bienvenida)
            self.broadcast(mensaje_bienvenida, cliente_envuelto)
            
            cliente_envuelto.send(f"Bienvenido al chat, {nombre_usuario}!".encode('utf-8'))
            cliente_envuelto.send("Escribe '/quit' para salir".encode('utf-8'))
            
            while True:
                mensaje = cliente_envuelto.recv(1024).decode('utf-8').strip()
                
                if not mensaje: continue
                
                if mensaje.lower() == '/quit': break
                elif mensaje.lower() == '/users':
                    usuarios = ", ".join(self.nombres_usuarios.values())
                    cliente_envuelto.send(f"👥 Usuarios conectados: {usuarios}".encode('utf-8'))
                else:
                    mensaje_completo = f"{nombre_usuario}: {mensaje}"
                    print(f"[{time.strftime('%H:%M:%S')}] {mensaje_completo}")
                    self.broadcast(mensaje_completo, cliente_envuelto)
                    
        except ConnectionResetError:
            print(f"⚠️  {nombre_usuario} se desconectó abruptamente")
        except Exception as e:
            print(f"❌ Error con cliente {nombre_usuario}: {e}")
        finally:
            self.eliminar_cliente(cliente_envuelto)

    def eliminar_cliente(self, cliente):
        """Elimina un cliente de las listas y cierra su conexión"""
        if cliente in self.clientes_conectados:
            nombre_usuario = self.nombres_usuarios.get(cliente, "Usuario desconocido")
            self.clientes_conectados.remove(cliente)
            if cliente in self.nombres_usuarios:
                del self.nombres_usuarios[cliente]
            
            mensaje_desconexion = f"👋 {nombre_usuario} ha abandonado el chat"
            print(mensaje_desconexion)
            self.broadcast(mensaje_desconexion)
            
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
                    # Aceptamos el socket envuelto en SSL
                    cliente_envuelto, direccion = self.socket_servidor.accept()
                    print(f"✅ Nueva conexión SEGURA desde {direccion[0]}:{direccion[1]}")
                    
                    hilo_cliente = threading.Thread(
                        target=self.manejar_cliente, 
                        args=(cliente_envuelto, direccion)
                    )
                    hilo_cliente.daemon = True
                    hilo_cliente.start()
                    
                    if len(self.clientes_conectados) % 5 == 0:
                        self.mostrar_estado()
                        
                except KeyboardInterrupt:
                    print("\n🛑 Deteniendo servidor...")
                    break
                except Exception as e:
                    print(f"❌ Error aceptando conexión: {e}")
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            print("\n🛑 Servidor interrumpido por el usuario")
        finally:
            self.cerrar_servidor()

    def cerrar_servidor(self):
        """Cierra todas las conexiones y el socket del servidor"""
        print("\n🔒 Cerrando todas las conexiones...")
        
        for cliente in self.clientes_conectados[:]:
            self.eliminar_cliente(cliente)
        
        if self.socket_servidor:
            self.socket_servidor.close()
            print("✅ Servidor cerrado correctamente")

if __name__ == "__main__":
    servidor = ServidorChat(host='localhost', puerto=9999)
    try:
        servidor.ejecutar()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
    finally:
        servidor.cerrar_servidor()
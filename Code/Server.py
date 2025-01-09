import socket
import struct
import time
import threading
import select


class Server:
    MAGIC_COOKIE = 0xabcddcba
    OFFER = 0x2
    REQUEST = 0x3
    PAYLOAD = 0x4

    def __init__(self):
        self.address = socket.gethostbyname(socket.gethostname())
        self.udp_port = 0
        self.tcp_port = 0
        self.running = threading.Event()
        self.UDP_socket = None
        self.TCP_socket = None

    def start(self):
        self.running.set()
        print(f'Server started, listening on IP address {self.address}')

        try:
            self.UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.UDP_socket.bind((self.address, 0))
            self.udp_port = self.UDP_socket.getsockname()[1]

            self.TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.TCP_socket.bind((self.address, 0))
            self.tcp_port = self.TCP_socket.getsockname()[1]
        except socket.error as e:
            print(f'Error: {e}')
            self.stop()
            return

        print(f'UDP port: {self.udp_port}, TCP port: {self.tcp_port}')

        broadcast_thread = threading.Thread(target=self.broadcast_offers)
        broadcast_thread.start()

        listen_TCP_thread = threading.Thread(target=self.listen_for_TCP_connections)
        listen_TCP_thread.start()

        listen_UDP_thread = threading.Thread(target=self.listen_for_UDP_connections)
        listen_UDP_thread.start()

        # TODO multithreading doesn't work
        try:
            self.running.wait()
        except KeyboardInterrupt:
            print("Keyboard interrupt received, stopping server.")
            self.stop()

    def broadcast_offers(self):
        """
        Broadcasts the server's IP address, UDP port and TCP port to the network

        :return: None
        """
        # Create the message to broadcast
        message = struct.pack('!I B H H', Server.MAGIC_COOKIE, Server.OFFER, self.udp_port, self.tcp_port)
        # TODO fix this while condition
        while self.running.is_set():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as socket_for_broadcast:
                socket_for_broadcast.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                try:
                    socket_for_broadcast.sendto(message, ('<broadcast>', 50000))
                except socket.error as e:
                    print(f"Broadcast error: {e}")
            time.sleep(1)

    def stop(self):
        self.running.clear()
        if self.UDP_socket:
            try:
                self.UDP_socket.close()
            except socket.error as e:
                print(f"Error closing UDP socket: {e}")

        if self.TCP_socket:
            try:
                self.TCP_socket.close()
            except socket.error as e:
                print(f"Error closing TCP socket: {e}")
        print('Server stopped')

    def listen_for_TCP_connections(self):
        pass

    def listen_for_UDP_connections(self):
        # TODO fix this while condition
        while self.running.is_set():
            readable, _, _ = select.select([self.UDP_socket], [], [], 1)
            for sock in readable:
                data, addr = sock.recvfrom(1024)
                print(f"Received UDP message from {addr}")
                self.handle_UDP_request(sock)

    def handle_TCP_request(self, sock: socket.socket):
        pass

    def handle_UDP_request(self, sock: socket.socket):
        pass

if __name__ == '__main__':
    server = Server()
    server.start()
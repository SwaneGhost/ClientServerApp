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
        self.broadcast_thread = None
        self.listen_TCP_thread = None
        self.listen_UDP_thread = None

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

        # Create threads for broadcasting the server's IP address and listening for TCP and UDP connections
        # daemon threads will be terminated when the main program exits - safer exit
        self.broadcast_thread = threading.Thread(target=self.broadcast_offers)
        self.broadcast_thread.daemon = True
        self.broadcast_thread.start()

        self.listen_TCP_thread = threading.Thread(target=self.listen_for_TCP_connections)
        self.listen_TCP_thread.daemon = True
        self.listen_TCP_thread.start()

        self.listen_UDP_thread = threading.Thread(target=self.listen_for_UDP_connections)
        self.listen_UDP_thread.daemon = True
        self.listen_UDP_thread.start()

        # Create a thread that waits for the user to press Ctrl+C to stop the server
        try:
            self.running.wait()  # Wait until the event is cleared - never
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

        if self.broadcast_thread:
            self.broadcast_thread.join()
        if self.listen_TCP_thread:
            self.listen_TCP_thread.join()
        if self.listen_UDP_thread:
            self.listen_UDP_thread.join()
        print('Server stopped')

    def listen_for_TCP_connections(self):
        # TODO remove after done debugging
        while self.running.is_set():
            print("Listening for TCP connections")
            time.sleep(3)

    def listen_for_UDP_connections(self):
        # TODO continue working on this function
        while self.running.is_set():
            print("Listening for UDP connections")
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
import math
import socket
import struct
import time
import threading

class Server:
    MAGIC_COOKIE = 0xabcddcba
    OFFER = 0x2
    REQUEST = 0x3
    PAYLOAD = 0x4
    PORT_FOR_OFFERS = 50000

    # ANSI escape codes for colors
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

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
        self.udp_mtu = 0

    def start(self) -> None:
        self.running.set()
        print(f'{self.GREEN}Server started, listening on IP address {self.address}{self.RESET}')

        try:
            self.UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.UDP_socket.bind((self.address, 0))
            self.udp_port = self.UDP_socket.getsockname()[1]
            self.udp_mtu = 1024 - 29

            self.TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.TCP_socket.bind((self.address, 0))
            self.tcp_port = self.TCP_socket.getsockname()[1]
        except socket.error as e:
            print(f'{self.RED}Error: {e}{self.RESET}')
            self.stop()
            return

        self.broadcast_thread = threading.Thread(target=self.broadcast_offers)
        self.broadcast_thread.start()

        self.listen_TCP_thread = threading.Thread(target=self.listen_for_TCP_connections)
        self.listen_TCP_thread.start()

        self.listen_UDP_thread = threading.Thread(target=self.listen_for_UDP_connections)
        self.listen_UDP_thread.start()

        print(f"{self.GREEN}Server listening on UDP port {self.udp_port} and TCP port {self.tcp_port}{self.RESET}")

    def broadcast_offers(self) -> None:
        message = struct.pack('!I B H H', Server.MAGIC_COOKIE, Server.OFFER, self.udp_port, self.tcp_port)
        while self.running.is_set():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as socket_for_broadcast:
                socket_for_broadcast.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                try:
                    socket_for_broadcast.sendto(message, ('<broadcast>', Server.PORT_FOR_OFFERS))
                except socket.error as e:
                    print(f"{self.RED}Broadcast error: {e}{self.RESET}")
            time.sleep(1)

    def stop(self) -> None:
        self.running.clear()
        if self.UDP_socket:
            try:
                self.UDP_socket.close()
            except socket.error as e:
                print(f"{self.RED}Error closing UDP socket: {e}{self.RESET}")

        if self.TCP_socket:
            try:
                self.TCP_socket.close()
            except socket.error as e:
                print(f"{self.RED}Error closing TCP socket: {e}{self.RESET}")

        if self.broadcast_thread and self.broadcast_thread.is_alive():
            self.broadcast_thread.join()
        if self.listen_TCP_thread and self.listen_TCP_thread.is_alive():
            self.listen_TCP_thread.join()
        if self.listen_UDP_thread and self.listen_UDP_thread.is_alive():
            self.listen_UDP_thread.join()
        print(f'{self.GREEN}Server closed successfully{self.RESET}')

    def listen_for_TCP_connections(self) -> None:
        self.TCP_socket.listen(10)
        while self.running.is_set():
            try:
                client_socket, client_address = self.TCP_socket.accept()
                tcp_thread = threading.Thread(target=self.handle_TCP_request, args=(client_socket, client_address))
                tcp_thread.daemon = True
                tcp_thread.start()
            except socket.error as e:
                if self.running.is_set():
                    print(f"{self.RED}Error accepting TCP connection: {e}{self.RESET}")

    def listen_for_UDP_connections(self) -> None:
        while self.running.is_set():
            try:
                data, addr = self.UDP_socket.recvfrom(1024)
                udp_thread = threading.Thread(target=self.handle_UDP_request, args=(data, addr))
                udp_thread.daemon = True
                udp_thread.start()
            except socket.error as e:
                if self.running.is_set():
                    print(f"{self.RED}Error receiving UDP data: {e}{self.RESET}")

    def handle_UDP_request(self, data: list, addr: str) -> None:
        try:
            if len(data) < 13:
                return
            magic_cookie, message_type, file_size = struct.unpack('!I B Q', data[:13])
            if magic_cookie != Server.MAGIC_COOKIE or message_type != Server.REQUEST:
                return

            number_of_segments = math.ceil(file_size / self.udp_mtu)
            current_segment = 0
            data = b'\xff' * file_size
            for i in range(number_of_segments):
                payload = data[i * self.udp_mtu: min((i + 1) * self.udp_mtu, len(data))]
                with_payload = struct.pack(f'!I B Q Q {len(payload)}s', Server.MAGIC_COOKIE, Server.PAYLOAD, number_of_segments, current_segment, payload)
                self.UDP_socket.sendto(with_payload, addr)
                current_segment += 1

        except socket.error as e:
            print(f"{self.RED}Error handling UDP request: {e}{self.RESET}")

    def handle_TCP_request(self, client_socket: socket.socket, client_address: str) -> None:
        try:
            file_size_string = client_socket.recv(1024).decode().strip()
            if not file_size_string.isdigit():
                print(f"{self.RED}Invalid file size: {file_size_string}{self.RESET}")
                return

            file_size = int(file_size_string)
            data = b'\xff' * file_size
            client_socket.sendall(data)
            print(f"{self.GREEN}Sent response to {client_address}{self.RESET}")
        except socket.error as e:
            print(f"{self.RED}Error handling TCP request: {e}{self.RESET}")
        finally:
            client_socket.close()

if __name__ == '__main__':
    server = Server()
    try:
        server.start()
        input("Press Enter to stop the server")
        server.stop()
    except KeyboardInterrupt:
        server.stop()
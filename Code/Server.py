import math
import socket
import struct
import time
import threading


class Server:
    """
    Server class for speed testing.
    The server broadcasts its IP address, UDP port, and TCP port to the network.
    The server listens for incoming TCP and UDP connections.
    The server sends a response message to the client with the same size as the file size received from the client.

    After debugging, check what print statements need to be removed.
    Use ANSI escape codes for colored output.
    """
    MAGIC_COOKIE = 0xabcddcba
    OFFER = 0x2
    REQUEST = 0x3
    PAYLOAD = 0x4
    PORT_FOR_OFFERS = 50000

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
        """
        Starts the server by creating a UDP and TCP socket and listening for incoming connections

        :return: None
        """
        self.running.set()
        print(f'Server started, listening on IP address {self.address}')

        try:
            # Create a UDP socket
            self.UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.UDP_socket.bind((self.address, 0))
            self.udp_port = self.UDP_socket.getsockname()[1]

            # Get the maximum segment size of the UDP socket
            self.udp_mtu = 1024 - 29 
            # remove our magic cookie message type segment count and segment number and potential udp header
            # self.udp_mtu -= 40

            # Create a TCP socket
            self.TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.TCP_socket.bind((self.address, 0))
            self.tcp_port = self.TCP_socket.getsockname()[1]
        except socket.error as e:
            print(f'Error: {e}')
            self.stop()
            return

        # Create threads for broadcasting the server's IP address and listening for TCP and UDP connections
        # daemon threads will be terminated when the main program exits - safer exit

        # Broadcast Thread to send offers to the network
        self.broadcast_thread = threading.Thread(target=self.broadcast_offers)
        self.broadcast_thread.start()

        # Listen for TCP connections Thread
        self.listen_TCP_thread = threading.Thread(target=self.listen_for_TCP_connections)
        self.listen_TCP_thread.start()

        # Listen for UDP connections Thread
        self.listen_UDP_thread = threading.Thread(target=self.listen_for_UDP_connections)
        self.listen_UDP_thread.start()

        print(f"Server listening on UDP port {self.udp_port} and TCP port {self.tcp_port}")

    def broadcast_offers(self)-> None:
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
                    socket_for_broadcast.sendto(message, ('<broadcast>', Server.PORT_FOR_OFFERS))
                except socket.error as e:
                    print(f"Broadcast error: {e}")
            time.sleep(1)

    def stop(self)-> None:
        """
        Stops the server by closing the UDP and TCP sockets and joining the broadcast and listen threads

        :return: None
        """
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

        # TODO consider removing the join calls
        if self.broadcast_thread and self.broadcast_thread.is_alive():
            self.broadcast_thread.join()
        if self.listen_TCP_thread and self.listen_TCP_thread.is_alive():
            self.listen_TCP_thread.join()
        if self.listen_UDP_thread and self.listen_UDP_thread.is_alive():
            self.listen_UDP_thread.join()
        print('Server closed successfully')

    def listen_for_TCP_connections(self) -> None:
        """
        Listens for incoming TCP connections and creates a new thread to handle each connection

        :return: None
        """
        self.TCP_socket.listen(10)  # Put the TCP socket in listening mode with a backlog of 10
        while self.running.is_set():
            try:
                # Blocking call to accept
                client_socket, client_address = self.TCP_socket.accept()
                tcp_thread = threading.Thread(target=self.handle_TCP_request, args=(client_socket, client_address))
                tcp_thread.daemon = True
                tcp_thread.start()
            except socket.error as e:
                if self.running.is_set():
                    print(f"Error accepting TCP connection: {e}")

    def listen_for_UDP_connections(self) -> None:
        """
        Listens for incoming UDP connections and creates a new thread to handle each connection

        :return: None
        """
        while self.running.is_set():
            try:
                data, addr = self.UDP_socket.recvfrom(1024)
                udp_thread = threading.Thread(target=self.handle_UDP_request, args=(data, addr))
                udp_thread.daemon = True
                udp_thread.start()
            except socket.error as e:
                if self.running.is_set():
                    print(f"Error receiving UDP data: {e}")

    def handle_UDP_request(self, data: list, addr: str) -> None:
        """
        Handles the received UDP request


        :return: None
        """
        try:
            # Handle the received data here
            # check for magic cookie for 4 then 1 then 8 bytes
            if len(data) < 13:
                return
            magic_cookie, message_type, file_size = struct.unpack('!I B Q', data[:13])
            print(magic_cookie == Server.MAGIC_COOKIE)
            if magic_cookie != Server.MAGIC_COOKIE:
                return
            if message_type != Server.REQUEST:
                return

            number_of_segments = math.ceil(file_size / self.udp_mtu)
            # Create a response message sized file_size
            current_segment = 0
            data = b'\xff' * file_size
            for i in range(number_of_segments):
                payload = data[i * self.udp_mtu: min((i + 1) * self.udp_mtu, len(data))]
                with_payload = struct.pack(f'!I B Q Q {len(payload)}s', Server.MAGIC_COOKIE, Server.PAYLOAD, number_of_segments, current_segment, payload)
                self.UDP_socket.sendto(with_payload, addr)
                current_segment += 1

        except socket.error as e:
            print(f"Error handling UDP request: {e}")

    def handle_TCP_request(self, client_socket: socket.socket, client_address: str) -> None:
        """
        Handles the received TCP request

        :return: None
        """

        try:
            # No need for magic cookie, message type, segment count, and segment number
            # Client sends the size of the file as a string ending with a newline

            # Read the file size as a string
            # Expected format "+digits\n"
            file_size_string = client_socket.recv(1024).decode().strip()
            # If the file size is not a valid integer, close the connection
            if not file_size_string.isdigit():
                print(f"Invalid file size: {file_size_string}")
                return

            # Convert the file size to an integer
            file_size = int(file_size_string)

            # Create a response message sized file_size
            data = b'\xff' * file_size

            # Send the response message
            client_socket.sendall(data)
            print(f"Sent response to {client_address}")
        except socket.error as e:
            print(f"Error handling TCP request: {e}")
        # Make sure the client socket is closed
        finally:
            client_socket.close()


if __name__ == '__main__':
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()

#TODO handle corrupted messages
#TODO handle client hanging up on tcp connection
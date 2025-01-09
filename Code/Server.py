import socket
import struct
import time
import threading

class Server:
    MAGIC_COOKIE = 0xabcddcba
    OFFER = 0x2
    REQUEST = 0x3
    PAYLOAD = 0x4

    def __init__(self):
        # TODO - change hardcoded values
        self.address = ''
        self.udp_port = 0
        self.tcp_port = 0
        self.running = False
        self.UDP_socket = None

    def start(self):
        """
        Start the server.

        :return: None
        """
        self.running = True
        print(f'Server started, listening on IP address {self.address}')

        # Create a UDP socket
        try:
            self.UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.UDP_socket.bind((self.address, 0))
            self.udp_port = self.UDP_socket.getsockname()[1]
        except socket.error as e:
            print(f'Error: {e}')
        finally:
            self.running = False
            return

        # Open broadcast_offers as a thread
        broadcast_thread = threading.Thread(target=self.broadcast_offers)
        broadcast_thread.start()


    def broadcast_offers(self):
        """
        Broadcasts offers to all clients using UDP.
        The server broadcasts messages every second.
        :return: None
        """

        # Pack the data into a binary format
        message = struct.pack('!I B H H', Server.MAGIC_COOKIE, Server.OFFER, self.udp_port, self.tcp_port)

        # While the server is running
        while self.running:
            # Create a UDP socket for broadcasting
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as socket_for_broadcast:
                # 50,000 is an arbitrary port number
                # Client will sniff out from all ports the broadcast
                socket_for_broadcast.sendto(message, ('255.255.255.255', 50000))
            # Sleep for 1 second
            time.sleep(1)

    def listen_for_TCP_requests(self):
        pass

    def listen_for_UDP_requests(self):
        pass



if __name__ == '__main__':
    pass
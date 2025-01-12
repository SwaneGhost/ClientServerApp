import socket
import struct
import threading
from scapy.all import sniff
from scapy.layers.inet import UDP, IP

# TODO check the reading size of the message

"""
workflow we understood so far:
1. we ask user for parameters to set up client
2. client listens to offer request and accepts the first offer and stops listening
3. client sends requests to server according to the parameters, x udp requests y tcp requests of size z data amount
4. client listens to each server response and times it
5. when all responses complete client returns to step 1 ?? or just ends


"""


class Client:
    MAGIC_COOKIE = 0xabcddcba
    OFFER = 0x2
    REQUEST = 0x3
    PAYLOAD = 0x4

    def __init__(self):
        self.server_address = None
        self.address = socket.gethostbyname(socket.gethostname())
        self.udp_port = 0
        self.tcp_port = 0
        self.udp_socket = 0
        self.tcp_socket = 0
        self.udp_threads = []
        self.tcp_threads = []
        self.broadcast_thread = None  #??? WHICH ONES DO WE NEED

        self.udp_mtu = 0

    def start(self):
        # request user input for parameters how many tcp and udp requests and how much data
        print("Enter the number of UDP requests: ")
        num_udp_requests = get_user_input()
        print("Enter the number of TCP requests: ")
        num_tcp_requests = get_user_input()
        print("Enter the amount of data (in bytes): ")
        data_amount = get_user_input()

        # listen to offer request
        print("“Client started, listening for offer requests...”.")
        # listen to first offer and stop listening
        sniff(prn=self.packet_callback, store=1, stop_filter=self.packet_callback)
        # take out server address
        # send udp requests
        for i in range(num_udp_requests):
            print(f"Sending UDP request {i + 1} to {self.address}")
            self.udp_threads.append(threading.Thread(target=self.udp_request, args=(data_amount,)))
            self.udp_threads[i].start()
        # send tcp requests
        for i in range(num_tcp_requests):
            print(f"Sending TCP request {i + 1} to {self.address}")
            self.tcp_threads.append(threading.Thread(target=self.tcp_request, args=(data_amount,)))
            self.tcp_threads[i].start()
        #TODO time the responses

        return

    def udp_request(self, data_amount) -> None:
        try:
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # set so two clients can use the same port when one is done
            #new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            # new_socket.bind((self.address, 0))
            packet = struct.pack('!I B Q', Client.MAGIC_COOKIE, Client.REQUEST, data_amount)
            new_socket.sendto(packet, (self.server_address, self.udp_port))
        except socket.error as e:
            print(f'Error: {e}')
            return

    def tcp_request(self, data_amount) -> None:
        try:
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_socket.connect((self.server_address, self.tcp_port))
            # new_socket.bind((self.address, 0))
            packet = struct.pack('!I B Q', Client.MAGIC_COOKIE, Client.REQUEST, data_amount)
            new_socket.send(packet)
            new_socket.close()
        except socket.error as e:
            print(f'Error: {e}')
            return

    def packet_callback(self, packet):
        if packet.haslayer(IP) and packet.haslayer(UDP):
            data = bytes(packet[UDP].payload)
            if len(data) >= 9:
                magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!I B H H', data[:9])
                if magic_cookie == Client.MAGIC_COOKIE and message_type == Client.OFFER:
                    print(f"Received offer from {packet[IP].src}")
                    # get server address and ports from packet
                    self.server_address = packet[IP].src
                    self.udp_port = udp_port
                    self.tcp_port = tcp_port
                    return True
        return False


def get_user_input():
    while True:
        check = input()
        if not check.isdigit() or int(check) <= 0:
            print("Please enter a valid integer above 0 , non integer values not allowed")
        else:
            return int(check)


if __name__ == '__main__':
    client = Client()
    client.start()

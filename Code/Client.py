import socket
import struct
import threading
import time
from scapy.layers.inet import UDP, IP

"""
missions:
1. add keyboard interrupt to stop the client and close the sockets 
2. check keyboard interrupt in the server
3. add fun prints and colors
4. choose team name - WAN DIRECTION
5. add comments to the code
6. check on two computers
"""


class Client:
    MAGIC_COOKIE = 0xabcddcba
    OFFER = 0x2
    REQUEST = 0x3
    PAYLOAD = 0x4
    PORT_FOR_OFFERS = 50000

    def __init__(self):
        self.server_address = None
        self.address = socket.gethostbyname(socket.gethostname())
        self.udp_port = 0
        self.tcp_port = 0
        self.udp_socket = 0
        self.tcp_socket = 0
        self.udp_threads = []
        self.tcp_threads = []
        self.udp_mtu = 0
        self.num_udp_requests = 0
        self.num_tcp_requests = 0
        self.data_amount = 0

    def start(self):
        # request user input for parameters how many tcp and udp requests and how much data
        print("Enter the number of UDP requests: ")
        self.num_udp_requests = get_user_input()
        print("Enter the number of TCP requests: ")
        self.num_tcp_requests = get_user_input()
        print("Enter the amount of data (in bytes): ")
        self.data_amount = get_user_input()

        # listen to offer request
        print("Client started, listening for offer requests...")
        while True:
            # listen to first offer and stop listening
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as offer_socket:
                offer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                offer_socket.bind((self.address, Client.PORT_FOR_OFFERS))
                while True:
                    data, addr = offer_socket.recvfrom(1024)
                    if len(data) >= 9:
                        magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!I B H H', data[:9])
                        if magic_cookie == Client.MAGIC_COOKIE and message_type == Client.OFFER:
                            print(f"Received offer from {addr[0]}")
                            self.server_address = addr[0]
                            self.udp_port = udp_port
                            self.tcp_port = tcp_port
                            break

            # send udp requests
            for i in range(self.num_udp_requests):
                print(f"Sending UDP request {i + 1} to {self.address}")
                self.udp_threads.append(threading.Thread(target=self.udp_request, args=(i+1,)))
                self.udp_threads[i].start()
            # send tcp requests
            for i in range(self.num_tcp_requests):
                print(f"Sending TCP request {i + 1} to {self.address}")
                self.tcp_threads.append(threading.Thread(target=self.tcp_request, args=(i+1,)))
                self.tcp_threads[i].start()

            # wait for all threads to finish
            # join all udp threads
            for thread in self.udp_threads:
                thread.join()
            # join all tcp threads
            for thread in self.tcp_threads:
                thread.join()

            self.udp_threads.clear()
            self.tcp_threads.clear()
            print("All transfers complete, listening to offer requests")


    def udp_request(self, thead_number: int) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as new_socket:
                # set so two clients can use the same port when one is done
                # new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                new_socket.bind((self.address, 0))
                packet = struct.pack('!I B Q', Client.MAGIC_COOKIE, Client.REQUEST, self.data_amount)
                start_time = time.perf_counter()
                new_socket.sendto(packet, (self.server_address, self.udp_port))
                new_socket.settimeout(1)
                arrived_segments = 0
                total_segments = 1
                total_data = 0
                while True:
                    try:
                        data, _ = new_socket.recvfrom(1024)
                        if len(data) < 13:
                            continue

                        magic_cookie, message_type, total_segments = struct.unpack('!I B Q', data[:13])
                        if magic_cookie != Client.MAGIC_COOKIE or message_type != Client.PAYLOAD:
                            print("Invalid packet")
                            continue

                        data = data[13:]
                        total_data += len(data)
                        arrived_segments += 1

                    except socket.timeout:
                        new_socket.close()
                        break

                end_time = time.perf_counter()
                total_time = end_time - start_time - 1
                print(f'UDP transfer #{thead_number} finished, '
                      f'total time: {total_time:.2f} seconds, '
                      f'total speed: {total_data * 8 / total_time:.2f} bits/second, '
                      f'percentage of packets received successfully: {arrived_segments / total_segments * 100:.2f}%')

        except socket.error as e:
            print(f'UDP Error: {e}')
            return

    def tcp_request(self, thread_number :int) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as new_socket:
                new_socket.connect((self.server_address, self.tcp_port))
                # new_socket.bind((self.address, 0))
                # Convert the file size to a string and append a newline character
                file_size_string = f'{self.data_amount}\n'
                packet = file_size_string.encode()
                start_time = time.perf_counter()
                new_socket.send(packet)



                # Receive the response
                received_data = b''
                while True:
                    chunk = new_socket.recv(1460)
                    if not chunk:
                        break
                    received_data += chunk
                new_socket.close()

                # end timing the response
                end_time = time.perf_counter()
                elapsed_time_sec = end_time - start_time

            print(f'TCP transfer #{thread_number} finished, '
                      f'total time: {elapsed_time_sec:.2f} seconds, '
                      f'total speed: {self.data_amount * 8 / elapsed_time_sec:.2f} bits/second')

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

import socket
import struct
import threading
import time
from scapy.layers.inet import UDP, IP


class Client:
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
        # Initialize client attributes
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
        # Start the client and listen for offer requests
        print(f"{self.CYAN}Enter the number of UDP requests: {self.RESET}")
        self.num_udp_requests = get_user_input()
        print(f"{self.CYAN}Enter the number of TCP requests: {self.RESET}")
        self.num_tcp_requests = get_user_input()
        print(f"{self.CYAN}Enter the amount of data (in bytes): {self.RESET}")
        self.data_amount = get_user_input()

        print(f"{self.GREEN}Client started, listening for offer requests...{self.RESET}")
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as offer_socket:
                offer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                offer_socket.bind((self.address, Client.PORT_FOR_OFFERS))
                while True:
                    data, addr = offer_socket.recvfrom(1024)
                    if len(data) >= 9:
                        magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!I B H H', data[:9])
                        if magic_cookie == Client.MAGIC_COOKIE and message_type == Client.OFFER:
                            self.server_address = addr[0]
                            self.udp_port = udp_port
                            self.tcp_port = tcp_port
                            break

            # Start threads for UDP and TCP requests
            for i in range(self.num_udp_requests):
                self.udp_threads.append(threading.Thread(target=self.udp_request, args=(i+1,)))
                self.udp_threads[i].start()
            for i in range(self.num_tcp_requests):
                self.tcp_threads.append(threading.Thread(target=self.tcp_request, args=(i+1,)))
                self.tcp_threads[i].start()

            # Wait for all threads to finish
            for thread in self.udp_threads:
                thread.join()
            for thread in self.tcp_threads:
                thread.join()

            self.udp_threads.clear()
            self.tcp_threads.clear()
            print(f"{self.GREEN}All transfers complete, listening to offer requests{self.RESET}")

    def udp_request(self, thread_number: int) -> None:
        # Handle UDP request
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as new_socket:
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
                            print(f"{self.RED}Invalid packet{self.RESET}")
                            continue

                        data = data[13:]
                        total_data += len(data)
                        arrived_segments += 1

                    except socket.timeout:
                        new_socket.close()
                        break

                end_time = time.perf_counter()
                if end_time == 0:
                    print(f"{self.RED}Server did not respond to UDP request #{thread_number}{self.RESET}")
                    return

                total_time = end_time - start_time - 1
                print(f"{self.GREEN}UDP transfer #{thread_number} finished, "
                      f"total time: {total_time:.2f} seconds, "
                      f"total speed: {total_data * 8 / total_time:.2f} bits/second, "
                      f"percentage of packets received successfully: {arrived_segments / total_segments * 100:.2f}%{self.RESET}")

        except socket.error as e:
            print(f"{self.RED}UDP Error: {e}{self.RESET}")
            return

    def tcp_request(self, thread_number: int) -> None:
        # Handle TCP request
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as new_socket:
                new_socket.settimeout(10)
                new_socket.connect((self.server_address, self.tcp_port))
                file_size_string = f'{self.data_amount}\n'
                packet = file_size_string.encode()
                start_time = time.perf_counter()
                new_socket.send(packet)

                received_data = b''
                while True:
                    try:
                        chunk = new_socket.recv(1460)
                        if not chunk:
                            break
                        received_data += chunk
                    except socket.timeout:
                        print(f"{self.RED}Server did not respond to TCP request #{thread_number}{self.RESET}")
                        return
                    received_data += chunk

                new_socket.close()
                end_time = time.perf_counter()
                elapsed_time_sec = end_time - start_time

            print(f"{self.GREEN}TCP transfer #{thread_number} finished, "
                  f"total time: {elapsed_time_sec:.2f} seconds, "
                  f"total speed: {self.data_amount * 8 / elapsed_time_sec:.2f} bits/second{self.RESET}")

        except socket.timeout:
            print(f"{self.RED}Server did not respond to TCP request #{thread_number}{self.RESET}")
            return

        except socket.error as e:
            print(f"{self.RED}Error: {e}{self.RESET}")
            new_socket.close()
            return

    def packet_callback(self, packet):
        # Handle packet callback for received offers
        if packet.haslayer(IP) and packet.haslayer(UDP):
            data = bytes(packet[UDP].payload)
            if len(data) >= 9:
                magic_cookie, message_type, udp_port, tcp_port = struct.unpack('!I B H H', data[:9])
                if magic_cookie == Client.MAGIC_COOKIE and message_type == Client.OFFER:
                    self.server_address = packet[IP].src
                    self.udp_port = udp_port
                    self.tcp_port = tcp_port
                    return True
        return False


def get_user_input():
    # Get user input and validate it
    while True:
        check = input()
        if not check.isdigit() or int(check) <= 0:
            print(f"{Client.RED}Please enter a valid integer above 0, non-integer values not allowed{Client.RESET}")
        else:
            return int(check)


if __name__ == '__main__':
    client = Client()
    client_thread = threading.Thread(target=client.start)
    client_thread.start()
    try:
        while client_thread.is_alive():
            client_thread.join(1)
    except KeyboardInterrupt:
        print(f"{Client.RED}KeyboardInterrupt detected, stopping the client...{Client.RESET}")
        client_thread.join()

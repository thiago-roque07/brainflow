import subprocess
import threading
import socket
import enum
import logging
import sys
import random
import time
import struct

from brainflow_emulator.emulate_common import TestFailureError, log_multilines


class State(enum.Enum):
    wait = 'wait'
    stream = 'stream'


class Message(enum.Enum):
    start_stream = b'b'
    stop_stream = b's'
    ack_values = (b'd', b'~6', b'~5', b'o', b'F0')
    ack_from_device = b'A'
    time_calc_command = b'F444'


class GaleaEmulator(object):

    def __init__(self):
        self.local_ip = '127.0.0.1'
        self.local_port = 2390
        self.server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.server_socket.settimeout(
            0.1)  # decreases sampling rate significantly because it will wait for recv 0.1 sec but it's just a test
        self.server_socket.bind((self.local_ip, self.local_port))
        self.state = State.wait.value
        self.addr = None
        self.package_num = 0
        self.base_package_size = 68
        self.exg_package_size = 52
        self.num_base_packages = 4
        self.num_exg_packages_per_base = 5
        self.bytes_in_single_entry = self.base_package_size + self.num_exg_packages_per_base * self.exg_package_size
        self.transaction_size = self.bytes_in_single_entry * self.num_base_packages

    def run(self):
        start_time = time.time()
        while True:
            try:
                msg, self.addr = self.server_socket.recvfrom(128)
                if msg == Message.start_stream.value:
                    self.state = State.stream.value
                elif msg == Message.stop_stream.value:
                    self.state = State.wait.value
                elif msg in Message.ack_values.value or msg.decode('utf-8').startswith('x'):
                    self.server_socket.sendto(Message.ack_from_device.value, self.addr)
                elif msg == Message.time_calc_command.value:
                    cur_time = time.time()
                    resp = bytearray(struct.pack('f', (cur_time - start_time) * 1000))
                    self.server_socket.sendto(resp, self.addr)
                else:
                    if msg:
                        # we dont handle board config characters because they dont change package format
                        logging.warn('received unexpected string %s', str(msg))
            except socket.timeout:
                logging.debug('timeout for recv')

            if self.state == State.stream.value:
                package = list()
                for _ in range(self.num_base_packages):
                    package.append(self.package_num)
                    self.package_num = self.package_num + 1
                    if self.package_num % 256 == 0:
                        self.package_num = 0
                    for i in range(1, self.base_package_size - 4):
                        package.append(random.randint(0, 255))
                    cur_time = time.time()
                    timestamp = bytearray(struct.pack('f', (cur_time - start_time) * 1000))
                    package.extend(timestamp)
                    for _ in range(self.num_exg_packages_per_base):
                        for i in range(self.exg_package_size - 4):
                            package.append(random.randint(0, 255))
                        cur_time = time.time()
                        timestamp = bytearray(struct.pack('f', (cur_time - start_time) * 1000))
                        package.extend(timestamp)
                # for gui
                eda = bytearray(struct.pack('f', random.random()))
                ppg_red = bytearray(struct.pack('i', int(random.random() * 5000)))
                ppg_ir = bytearray(struct.pack('i', int(random.random() * 5000)))
                battery = bytearray(struct.pack('i', int(random.random() * 100)))
                for i in range(1, 5):
                    package[i] = eda[i - 1]
                for i in range(60, 64):
                    package[i] = ppg_ir[i - 60]
                for i in range(56, 60):
                    package[i] = ppg_red[i - 56]
                package[53] = random.randint(0, 100)
                try:
                    self.server_socket.sendto(bytes(package), self.addr)
                except socket.timeout:
                    logging.info('timeout for send')


def main():
    emulator = GaleaEmulator()
    emulator.run()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO)
    main()

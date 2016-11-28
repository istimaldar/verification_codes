import serial
import threading
import math
import crcmod


def hemming_encode_one(message):
    int_message = 0
    for number, current in enumerate(message):
        int_message += current << (8 * number)
    bit_message = [int(current) for current in bin(int_message)[2:]]
    while len(bit_message) % 8:
        bit_message = [0] + bit_message
    for i in [0, 1, 3, 7]:
        bit_message.insert(i, 0)
    for i in range(math.trunc(math.log(len(bit_message), 2))):
        bit = 0
        for number, current in enumerate(bit_message):
            if int('{:<0{first}}'.format(bin(number+1)[:1:-1], first=int(math.log(len(bit_message), 2)+1))[i]) == 1:
                bit ^= current
        bit_message[2 ** i - 1] = bit
    return bit_message


def hemming_decode_one(message):
    bit_message = []
    int_message = [int(current) for current in message]
    for cur in int_message:
        bit_message += [int(current) for current in '{:>08}'.format(bin(cur)[2:])]
    bit_message = [bit_message[:12], bit_message[-12:]]
    result = []
    for current_bytes in bit_message:
        i = 0
        error_check = [0, 0, 0, 0]
        while i < math.log(len(current_bytes), 2):
            for number, current in enumerate(current_bytes):
                if int('{:<0{first}}'.format(bin(number+1)[:1:-1], first=4)[i]) == 1:
                    error_check[i] ^= current
            i += 1
        wrong_bit = 0
        for n, i in enumerate(error_check):
            wrong_bit += i * (2 ** n)
        if wrong_bit:
            current_bytes[wrong_bit-1] = 1 - current_bytes[wrong_bit-1]
        result += [bit for num, bit in enumerate(current_bytes) if num not in [2 ** i - 1 for i in range(5)]]
    return result


def pack_two(data):
    current = iter(data)
    return zip(current, current)


def pack_three(data):
    current = iter(data)
    return zip(current, current, current)


def hemming_encode(message):
    encoded = []
    if len(message) % 2:
        message += b'\x00'
    try:
        for first, second in pack_two(message):
            current = hemming_encode_one([first]) + hemming_encode_one([second])
            encoded += current
    except FileNotFoundError:
        pass
    return to_bytes(encoded)


def hemming_decode(message):
    decoded = []
    for block in pack_three(message):
            current = hemming_decode_one(block)
            decoded += current
    return to_bytes(decoded)


def to_bytes(message):
    message.reverse()
    output = []
    for number, bit in enumerate(message):
        if not number % 8:
            output.append(bit)
        else:
            output[number//8] += bit * (2 ** (number % 8))
    output.reverse()
    return bytes(output)


class PairOfPorts():
    def __init__(self, port, func=(lambda string: print(string))):
        self.WritingPort = serial.Serial(port, timeout=1)
        self.ReadingPort = serial.Serial(port, timeout=1)
        read_thread = threading.Thread(target=self.read, name="reader", args=[func])
        self.need_to_read = True
        read_thread.start()

    def write(self, data):
        message = data.encode("ascii")
        message = hemming_encode(message)
        message.replace(b'\x7e', b'\x7d\x5e')
        message.replace(b'\x7d', b'\x7d\x5d')
        message.replace(b'\x7c', b'\x7b\x5c')
        message.replace(b'\x7b', b'\x7b\x5b')
        message = b'\x7e' + message + b'\x7c'
        self.WritingPort.write(message)

    def read(self, func=(lambda string: print(string))):
        while self.need_to_read:
            message = b''
            data = self.ReadingPort.read(1)
            if data != b'\x7e':
                continue
            else:
                data = self.ReadingPort.read(1)
            while data != b'\x7c':
                message += data
                data = self.ReadingPort.read(1)
            if len(message):
                data.replace(b'\x7d\x5e', b'\x7e')
                data.replace(b'\x7d\x5d', b'\x7d')
                data.replace(b'\x7b\x5c', b'\x7c')
                data.replace(b'\x7b\x5b', b'\x7b')
                func(hemming_decode(message))

    def add_crc(self):
        pass

    def stop(self):
        self.need_to_read = False
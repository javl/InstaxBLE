#!/usr/bin/env python3

from events import EventType
from struct import pack
import asyncio
from bleak import BleakScanner
import socket


class InstaxBle:
    def __init__(self, printEnabled=False, printerName=None):
        """
        Initialize the InstaxBle class.
        printEnabled: by default, actual printing is disabled to prevent misprints.
        printerName: if specified, will only connect to a printer with this name.
        """
        self.printEnabled = printEnabled
        self.isConnected = False
        self.device = None
        self.printerName = printerName
        self.sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

    def connect(self, timeout=0):
        """ Connect to the printer. Quit trying after timeout seconds. """
        self.isConnected = False
        self.device = asyncio.run(self.find_device(timeout=timeout))
        if self.device:
            print(f'found device {self.device.name}, connecting...')
            try:
                self.sock.connect((self.device.address, 6))
                self.isConnected = True
                print('connected')
            except Exception as e:
                print(f'connection failed: {e}')

    def disconnect(self):
        if self.isConnected:
            self.socket.disconnect()

    def enable_printing(self):
        """ Enable printing. """
        self.printEnabled = True

    def disable_printing(self):
        """ Disable printing. """
        self.printEnabled = False

    async def find_device(self, timeout=0, mode='ANDROID'):
        """" Scan for our device and return it when found """
        print('Looking for instax printer...')
        secondsTried = 0
        while True:
            devices = await BleakScanner.discover(timeout=1)
            for device in devices:
                # if (self.printerName is None and dev.name.startswith('INSTAX-') and dev.name.endswith(mode)) or \
                if (self.printerName is None and device.name.startswith('INSTAX-') and device.name.endswith(f'({mode})')) or \
                   device.name == self.printerName:
                    return device
            secondsTried += 1
            if timeout != 0 and secondsTried >= timeout:
                return None

    def create_color_payload(self, colorArray, speed, repeat, when):
        """
        Create a payload for a color pattern.
        colorArray: array of RGB values to use in animation, e.g. [[255, 0, 0], [0, 255, 0], [0, 0, 255]]
        speed: time per frame/color. Higher is slower animation
        repeat: 0 = don't repeat (so play once), 1-254 = times to repeat, 255 = repeat forever
        when: 0 = normal, 1 = on print, 2 = on print completion, 3 = pattern switch
        """

        payload = pack('BBBB', when, len(colorArray), speed, repeat)
        for color in colorArray:
            payload += pack('BBB', color[0], color[1], color[2])
        return payload

    def send_led_pattern(self, pattern, speed=5, repeat=255, when=0):
        """ Send a LED pattern to the Instax printer. """
        payload = self.create_color_payload(pattern, speed, repeat, when)
        packet = self.create_packet(EventType.LED_PATTERN_SETTINGS, payload)
        return self.send_packet(packet)

    def prettify_bytearray(self, value):
        """ Helper funtion to convert a bytearray to a string of hex values. """
        return ' '.join([f'{x:02x}' for x in value])

    def create_checksum(self, bytearray):
        """ Create a checksum for a given packet. """
        return (255 - (sum(bytearray) & 255)) & 255

    def create_packet(self, eventType, payload=b''):
        """ Create a packet to send to the printer. """
        if isinstance(eventType, EventType):  # allows passing in an event or a value directly
            eventType = eventType.value

        header = b'\x41\x62'  # Ab from client to printer, Ba from printer to client
        opCode = bytes([eventType[0], eventType[1]])
        packetSize = pack('>H', 7 + len(payload))
        packet = header + packetSize + opCode + payload
        packet += pack('B', self.create_checksum(packet))
        return packet

    def validate_checksum(self, packet):
        """ Validate the checksum of a packet. """
        return (sum(packet) & 255) == 255

    # async def send_color(self):
    #     """ send a color pattern """
    #     im = Image.open('gradient.jpg')
    #     px = im.load()
    #     size = im.size if im._getexif().get(274, 0) < 5 else im.size[::-1]
    #     colorArray = []
    #     for x in range(0, size[0], 20):
    #         color = im.getpixel((x, 0))
    #         colorArray.append([color[0], color[1], color[2]])

    #     payload = self.create_color_payload(colorArray, 10, 255)
    #     packet = self.create_packet(EventType.LED_PATTERN_SETTINGS, payload)

    #     sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    #     sock.connect((self.device.address, 6))
    #     sock.send(packet)
    #     resp = sock.recv(8)
    #     sock.close()
    #     return resp

    def send_packet(self, packet):
        """ Send a packet to the printer. """
        # print("sending: ", self.prettify_bytearray(packet))
        if self.isConnected:
            self.sock.send(packet)
            # print('sent')
            response = self.sock.recv(64)
            self.sock.close()
            return response

    # TODO: printer doesn't seem to respond to this
    # def shut_down(self):
    #     """ Shut down the printer. """
    #     packet = self.create_packet(EventType.SHUT_DOWN)
    #     return self.send_packet(packet)

    def image_to_bytes(self, imagePath):
        """ Convert an image to a bytearray """
        imgdata = None
        try:
            with open(imagePath, "rb") as image:
                imgdata = bytearray(image.read())
            return imgdata
        except Exception as e:
            print('Error loading image: ', e)

    def print_image(self, imagePath):
        """ print an image """
        imgData = self.image_to_bytes(imagePath)
        printCommands = [
            self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_START, b'\x02\x00\x00\x00\x00\x00' + pack('>H', len(imgData)))
        ]

        # divide image data up into chunks of 900 bytes and pad the last chunk with 0s if needed
        imgDataChunks = [imgData[i:i + 900] for i in range(0, len(imgData), 900)]
        if len(imgDataChunks[-1]) < 900:
            imgDataChunks[-1] = imgDataChunks[-1] + bytes(900 - len(imgDataChunks[-1]))

        for index, chunk in enumerate(imgDataChunks):
            imgDataChunks[index] = pack('>I', index) + chunk  # add chunk number as int (4 bytes)
            printCommands.append(self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_DATA, pack('>I', index) + chunk))

        printCommands.extend([
            self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_END),
            self.create_packet(EventType.PRINT_IMAGE),
            self.create_packet((0, 2), b'\x02'),
        ])

        if not self.printEnabled:
            return "Printing is disabled"

        for index, packet in enumerate(printCommands):
            print(f'sending image packet {index+1}/{len(printCommands)}')
            self.send_packet(packet)
            # print(f'({len(packet)}) {self.prettify_bytearray(packet[:40])}')


if __name__ == '__main__':
    instax = InstaxBle()
    # uncomment the next line to enable actual printing
    # instax.enable_printing()
    instax.connect()
    if instax.isConnected:
        instax.send_led_pattern([[255, 0, 0], [0, 255, 0], [0, 0, 255]])
        instax.print_image('example.jpg')
    instax.disconnect()

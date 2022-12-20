#!/usr/bin/env python3

from events import EventType
from struct import pack, unpack_from
import asyncio
from bleak import BleakScanner, BleakClient
import LedPatterns

class InstaxBle:
    def __init__(self, printEnabled=False, printerName=None):
        """
        Initialize the InstaxBle class.
        printEnabled: by default, actual printing is disabled to prevent misprints.
        printerName: if specified, will only connect to a printer with this name.
        """
        self.printEnabled = printEnabled
        self.device = None
        self.printerName = printerName
        self.writeUUID = '70954783-2d83-473d-9e5f-81e1d02d5273'
        self.notifyUUID = '70954784-2d83-473d-9e5f-81e1d02d5273'
        self.client = BleakClient(None)

    def notification_handler(self, characteristic, packet):
        if len(packet) < 8:
            print(f"Error: response packet size should be >= 8 (was {len(packet)})")
            raise
        elif not self.validate_checksum(packet):
            print("Checksum validation error")
            raise

        # header, length, op1, op2 = unpack_from('<HHBB', packet)
        # print('header: ', header, '\t', self.prettify_bytearray(packet[0:2]))
        # print('length: ', length, '\t', self.prettify_bytearray(packet[2:4]))
        # print('op1: ', op1, '\t\t', self.prettify_bytearray(packet[4:5]))
        # print('op2: ', op2, '\t\t', self.prettify_bytearray(packet[5:6]))

        # # data = packet[4:-1]  # the packet without header and checksum
        # data = packet[6:-1]  # the packet without headers and checksum
        # print(f'Response data: {data} (length: {len(data)}, checksum OK)')
        # print(f'  {self.prettify_bytearray(data)}')


    async def connect(self, timeout=0):
        """ Connect to the printer. Quit trying after timeout seconds. """
        # self.isConnected = False
        self.device = await self.find_device(timeout=timeout)
        if self.device:
            try:
                self.client = BleakClient(self.device.address)
                if not self.client.is_connected:
                    await self.client.connect()
                await self.client.start_notify(self.notifyUUID, self.notification_handler)
            except Exception as e:
                print('error on attaching notification_handler: ', e)

    async def disconnect(self):
        if self.client:
            if self.client.is_connected:
                await self.client.disconnect()

    def enable_printing(self):
        """ Enable printing. """
        self.printEnabled = True

    def disable_printing(self):
        """ Disable printing. """
        self.printEnabled = False

    async def find_device(self, timeout=0, mode='IOS'):
        """" Scan for our device and return it when found """
        print('Looking for instax printer...')
        secondsTried = 0
        while True:
            devices = await BleakScanner.discover(timeout=1)
            for device in devices:
                if device.name.startswith('INSTAX-'):
                    print(device.name)
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

    async def send_packet(self, packet):
        """ Send a packet to the printer. """
        if self.client:
            if not self.client.is_connected:
                await self.client.connect()
            await self.client.write_gatt_char(self.writeUUID, packet)
        else:
            print("no client to send packet to")

    # TODO: printer doesn't seem to respond to this
    # async def shut_down(self):
    #     """ Shut down the printer. """
    #     packet = self.create_packet(EventType.SHUT_DOWN)
    #     return await self.send_packet(packet)

    def image_to_bytes(self, imagePath):
        """ Convert an image to a bytearray """
        imgdata = None
        try:
            # TODO: I think returning image.read() already returns bytes so no need for bytearray?
            with open(imagePath, "rb") as image:
                imgdata = bytearray(image.read())
            return imgdata
        except Exception as e:
            print('Error loading image: ', e)

    async def print_image(self, imgSrc):
        """
        print an image. Either pass a path to an image (as a string) or pass
        the bytearray to print directly
        """
        imgData = imgSrc
        if isinstance(imgSrc, str):  # if it's a path, load the image contents
            imgData = self.image_to_bytes(imgSrc)

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
            print( "Printing is disabled")
            return

        for index, packet in enumerate(printCommands):
            # TODO: after each packet wait for the server's response before sending
            # the next one, instead of with a fixed delay as we do now
            await asyncio.sleep(0.05)
            print(f'sending image packet {index+1}/{len(printCommands)}')
            await self.send_packet(packet)

async def main():
    instax = InstaxBle()
    # instax.enable_printing()  # uncomment this line to enable actual printing
    await instax.connect()
    await instax.send_led_pattern(LedPatterns.pulseGreen)
    await instax.print_image('example.jpg')
    await instax.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

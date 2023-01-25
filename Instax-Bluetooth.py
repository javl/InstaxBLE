#! /usr/bin/env python3
from Types import EventType, InfoType
from struct import pack, unpack_from
import asyncio
from bleak import BleakScanner
import sys


if sys.platform == 'linux':
    from InstaxLinux import InstaxLinux as InstaxPlatform
else:
    from InstaxMacos import InstaxMacos as InstaxPlatform


class InstaxBluetooth(InstaxPlatform):
    def __init__(self, deviceAddress=None, deviceName=None, printEnabled=False, printerName=None):
        """
        Initialize the InstaxBluetooth class.
        printEnabled: by default, actual printing is disabled to prevent misprints.
        printerName: if specified, will only connect to a printer with this name.
        """
        # super(InstaxPlatform, self).__init__(*args, **kwargs)

        self.printEnabled = printEnabled
        self.isConnected = False
        self.device = None
        self.deviceAddress = deviceAddress
        self.deviceName = deviceName
        self.batteryState = None
        self.batteryPercentage = None
        self.printsLeft = None

        # Call platform specific init
        super(InstaxPlatform, self).__init__()

    def enable_printing(self):
        """ Enable printing. """
        self.printEnabled = True

    def disable_printing(self):
        """ Disable printing. """
        self.printEnabled = False

    # async def find_device(self, timeout=0, mode='ANDROID'):
    #     """" Scan for our device and return it when found """
    #     print('Looking for instax printer...')
    #     secondsTried = 0
    #     while True:
    #         devices = await BleakScanner.discover(timeout=1)
    #         for device in devices:
    #             if (self.deviceName is None and device.name.startswith('INSTAX-')) or \
    #                device.name == self.deviceName or device.address == self.deviceAddress:
    #                 if device.address.startswith('FA:AB:BC'):  # found the IOS endpoint, convert to ANDROID
    #                     device.address = device.address.replace('FA:AB:BC', '88:B4:36')
    #                     device.name = device.name.replace('IOS', 'ANDROID')
    #                 return device
    #         secondsTried += 1
    #         if timeout != 0 and secondsTried >= timeout:
    #             return None

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

    def get_device_state(self):
        """ Get device state, like battery level, if it is
        charging, number of prints left, etc. """
        packet = self.create_packet(EventType.SUPPORT_FUNCTION_INFO, bytes([InfoType.BATTERY_INFO.value]))
        resp = self.send_packet(packet)
        self.parse_response(resp)

        packet = self.create_packet(EventType.SUPPORT_FUNCTION_INFO, bytes([InfoType.PRINTER_FUNCTION_INFO.value]))
        resp = self.send_packet(packet)
        self.parse_response(resp)

    # TODO: printer doesn't seem to respond to this?
    # def shut_down(self):
    #     """ Shut down the printer. """
    #     packet = self.create_packet(EventType.SHUT_DOWN)
    #     return self.send_packet(packet)

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

    def print_image(self, imgSrc):
        """ print an image. Either pass a path to an image or a bytearray"""
        if isinstance(imgSrc, str):  # if it's a path, load the image contents
            imgData = self.image_to_bytes(imgSrc)
        else:  # the data passed is the image itself
            imgData = imgSrc

        printCommands = [
            self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_START, b'\x02\x00\x00\x00\x00\x00' + pack('>H', len(imgData)))
        ]

        # divide image data into chunks of 900 bytes and pad the last chunk with zeroes if needed
        imgDataChunks = [imgData[i:i + 900] for i in range(0, len(imgData), 900)]
        if len(imgDataChunks[-1]) < 900:
            imgDataChunks[-1] = imgDataChunks[-1] + bytes(900 - len(imgDataChunks[-1]))

        for index, chunk in enumerate(imgDataChunks):
            imgDataChunks[index] = pack('>I', index) + chunk  # add chunk number as int (4 bytes)
            printCommands.append(self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_DATA, pack('>I', index) + chunk))

        if self.printEnabled:
            printCommands.extend([
                self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_END),
                self.create_packet(EventType.PRINT_IMAGE),
                self.create_packet((0, 2), b'\x02'),
            ])
        else:
            print("Printing is disabled. Sending all packets except for PRINT_IMAGE command")

        for index, packet in enumerate(printCommands):
            print(f'sending image packet {index+1}/{len(printCommands)}')
            self.send_packet(packet)

    def get_accelerometer(self):
        """ Get accelerometer data from the printer. """
        packet = self.create_packet(EventType.XYZ_AXIS_INFO)
        resp = self.send_packet(packet)
        self.parse_response(resp)


def main():
    """ Example usage of the Instax-Bluetooth module """
    # let the module search for the first instax printer it finds
    # instax = InstaxBluetooth()
    # or specify your device address to skip searching
    instax = InstaxBluetooth(deviceAddress='88:B4:36:4E:20:CE')

    # uncomment the next line to enable actual printing
    # otherwise it will go through the whole printing process except
    # for sending the final 'go print' command
    # instax.enable_printing()
    instax.connect()
    if instax.isConnected:
        instax.send_led_pattern([[255, 0, 0], [0, 255, 0], [0, 0, 255]])
        # instax.print_image('example.jpg')
        instax.get_device_state()
        # instax.get_accelerometer()
        # instax.print_image('example.jpg')


if __name__ == '__main__':
    main()

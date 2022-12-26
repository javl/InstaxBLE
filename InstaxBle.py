#!/usr/bin/env python3

from EventType import EventType
from struct import pack, unpack_from
import asyncio
from bleak import BleakScanner, BleakClient
import LedPatterns
import logging
from random import randint
from time import sleep

"""
The InstaxBle class is used to communicate with the Instax printer over BLE.
These prints advertise themselves with the name 'INSTAX-xxx (IOS)' and 'INSTAX-xxx (Android)',
which use slightly different communications methods. This class will try to connect to the
printer with the name 'INSTAX-xxx (IOS)' and communicates over gatt (in contrast to the Android
one that uses a socket) which seems to be platform independents. Plus, the Raspberry Pi doesn't
seem to pick up the Android printer at all.
"""


class InstaxBle:
    def __init__(self, address=None, printerName=None, debug=False):
        """
        Initialize the InstaxBle class. If address is specified, will connect to that device.
        If printerName is specified, will only connect to a printer with this name.
        """
        self.writeUUID = '70954783-2d83-473d-9e5f-81e1d02d5273'
        self.notifyUUID = '70954784-2d83-473d-9e5f-81e1d02d5273'

        self.address = address
        self.printerName = printerName

        self.client = BleakClient(None)
        self.debug = debug
        self.printingEnabled = True

        self.imageDataQueue = []
        self.responseEventTypeSent = None
        self.responseEventTypeReceived = False

        self.imageChunkSize = 900  # images are up into chunks of 900 bytes for the 4:3 images
        self.maxPacketSize = 20  # Chop packets into smaller ones of this size, to be sent in sequence

        # self.event_loop = None  # .new_event_loop()
        # try:
        #     self.event_loop = asyncio.get_event_loop()
        # except RuntimeError:
        #     print('make our own event loop')
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)

        if not address:
            self.address = self.event_loop.run(self.find_device())
            if self.address is None:
                print('No printer found')
                return

    async def find_device(self, timeout=0):
        """"
        Scan for BLE devices to try and find our Instax printer.
        If timeout is specified, will stop scanning after that many seconds.

        Returns one of the following:
        1) the address of the device with the specified name
        2) the address of the first device that starts with 'INSTAX-' (of no name is specified)
        3) 'None' if no device was found
        """
        if self.debug:
            print('Looking for instax printer...')
        secondsTried = 0
        while True:
            devices = await BleakScanner.discover(timeout=1)
            for device in devices:
                if self.debug and device.name.startswith('INSTAX-'):
                    print(device.name)
                if (self.printerName is None and device.name.startswith('INSTAX-') and device.name.endswith('(IOS)')) \
                   or device.name == self.printerName:
                    if self.debug:
                        print(f'Found printer: {device.name} at {device.address}')
                    return device.address
            secondsTried += 1
            if timeout != 0 and secondsTried >= timeout:
                return None

    async def ensure_connection(self):
        """" Ensure that we are connected to the printer. """
        if not self.client.is_connected:
            if self.client.address is None:
                self.client = BleakClient(self.address)
            await self.client.connect()
        await self.client.start_notify(self.notifyUUID, self.notification_handler)

    def notification_handler(self, characteristic, packet):
        print(f'\nat notification_handler, characteristic: {characteristic}')
        if len(packet) < 8:
            print(f"Error: response packet size should be >= 8 (was {len(packet)})")
            raise
        elif not self.validate_checksum(packet):
            print("Checksum validation error")
            raise

        op1, op2 = unpack_from('<BB', packet[4:6])
        reponseEventType = EventType((op1, op2))
        self.responseEventTypeReceived = reponseEventType

    def disconnect(self):
        """ Disconnect from the printer. """
        if self.client.is_connected:
            print('disconnecting...')
            self.event_loop.run_until_complete(self.client.disconnect())

    def enable_printing(self):
        """ Enable printing. """
        self.printingEnabled = True

    def disable_printing(self):
        """ Disable printing. """
        self.printingEnabled = False

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

    # async def _await_send_packet(self, cmdEventType, packet, waitForResponse=True):
    #     await self.send_packet(cmdEventType, packet, waitForResponse)

    def send_led_pattern(self, pattern, speed=5, repeat=255, when=0):
        """ Send a LED pattern to the Instax printer. """
        payload = self.create_color_payload(pattern, speed, repeat, when)
        packet = self.create_packet(EventType.LED_PATTERN_SETTINGS, payload)
        # self.event_loop.run_until_complete(self._await_send_packet(EventType.LED_PATTERN_SETTINGS, packet))
        self.event_loop.run_until_complete(self.send_packet(EventType.LED_PATTERN_SETTINGS, packet, True))

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

    async def wait_for_response(self, responseExcpected):
        """"
        Wait for a response from the printer.
        """
        while not self.responseEventTypeReceived:
            await asyncio.sleep(0.01)

        print(f'Notices new response: {self.responseEventTypeReceived} received')
        eventTypeReceived = self.responseEventTypeReceived

        if eventTypeReceived == responseExcpected:
            print(f"is what we are waiting for: {eventTypeReceived} == {responseExcpected}")
        else:
            print(f"is NOT what we are waiting for: {eventTypeReceived} == {responseExcpected}")
        self.responseEventTypeReceived = None
        self.responseEventTypeSent = None

        if eventTypeReceived == EventType.LED_PATTERN_SETTINGS:
            # Led pattern settings response, nothing to do
            pass

        elif eventTypeReceived in [EventType.PRINT_IMAGE_DOWNLOAD_START, EventType.PRINT_IMAGE_DOWNLOAD_DATA]:
            # Image download start or data, send next part
            print('image parts left: ', len(self.imageDataQueue), 'parts')
            if len(self.imageDataQueue) > 0:
                next_packet = self.imageDataQueue.pop(0)
                await self.send_packet(EventType.PRINT_IMAGE_DOWNLOAD_DATA, next_packet, False)
            else:
                print('end of image data, so send the final packet')
        else:
            print('uncaught response:', eventTypeReceived)

    async def send_packet(self, cmdEventType, packet, waitForResponse=True):
        """ Send a packet to the printer. """
        await self.ensure_connection()
        for i in range(0, len(packet), self.maxPacketSize):
            """ Send the packet in chunks of maxPacketSize.
            We don't wait for response after each chunk, but after the whole packet."""
            # print("send packet: ", self.prettify_bytearray(packet[i:i + self.maxPacketSize][:30]))
            self.responseEventTypeReceived = None
            self.responseEventTypeSent = cmdEventType
            await self.client.write_gatt_char(self.writeUUID, packet[i:i + self.maxPacketSize])
        if waitForResponse:
            print('awaiting response...')
            await self.wait_for_response(cmdEventType)

    async def get_status(self):
        """ Get the printer status. """
        packet = self.create_packet(EventType.STATUS)
        await self.send_packet(packet)

    # TODO: printer doesn't seem to respond to this
    # async def reset(self):
    #     """ Reset the printer. """
    #     packet = self.create_packet(EventType.RESET)
    #     await self.send_packet(packet)

    # TODO: printer doesn't seem to respond to this
    # async def shut_down(self):
    #     """ Shut down the printer. """
    #     packet = self.create_packet(EventType.SHUT_DOWN)
    #     await self.send_packet(packet)

    # def wait(self, seconds):
    #     """ Wait for a given number of seconds. """
    #     # self.event_loop.sleep(seconds)

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

    async def _print_image(self, imgSrc):
        """
        print an image. Either pass a path to an image (as a string) or pass
        the bytearray to print directly

        Images are cut up into chunks of <imageChunkSize> size (and padded with 0s if needed for the last part)
        These chunks in turn get sent to the printer in snippets of <maxPacketSize> size.
        """
        print('send image')
        self.printPacketQueue = []
        imgData = imgSrc
        if isinstance(imgSrc, str):  # if it's a path, load the image contents
            imgData = self.image_to_bytes(imgSrc)

        # divide image data up into chunks of 900 bytes and pad the last chunk with 0s if needed
        self.imageDataQueue = []
        imgDataChunks = [imgData[i:i + self.imageChunkSize] for i in range(0, len(imgData), self.imageChunkSize)]
        if len(imgDataChunks[-1]) < self.imageChunkSize:
            imgDataChunks[-1] = imgDataChunks[-1] + bytes(self.imageChunkSize - len(imgDataChunks[-1]))

        for index, chunk in enumerate(imgDataChunks):
            imgDataChunks[index] = pack('>I', index) + chunk  # add chunk number as int (4 bytes)
            packet = self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_DATA, pack('>I', index) + chunk)
            self.imageDataQueue.append(packet)
        # print('total parts: ', len(self.imageDataQueue))

        # printCommands.extend([
        #     self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_END),
        #     self.create_packet(EventType.PRINT_IMAGE),
        #     self.create_packet((0, 2), b'\x02'),
        # ])

        if not self.printingEnabled:
            print("Printing is disabled. To enable call enable_printing() first")
            return

        printStartCmd = self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_START, b'\x02\x00\x00\x00\x00\x00' + pack('>H', len(imgData)))
        await self.send_packet(EventType.PRINT_IMAGE_DOWNLOAD_START, printStartCmd, True)
        print("go send parts")
        # await self.wait_for_response(EventType.PRINT_IMAGE_DOWNLOAD_START)
        for index, packet in enumerate(self.imageDataQueue):
            # print(f'sending image packet {index+1}/{len(self.imageDataQueue)}')
            await self.send_packet(EventType.PRINT_IMAGE_DOWNLOAD_DATA, packet, False)
        print('sent all parts')

        printEndCmd = self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_END)
        await self.send_packet(EventType.PRINT_IMAGE_DOWNLOAD_END, printEndCmd, True)

        printCmd = self.create_packet(EventType.PRINT_IMAGE)
        await self.send_packet(EventType.PRINT_IMAGE, printCmd, True)

        # for index, packet in enumerate(printCommands):
        #     # TODO: after each packet wait for the server's response before sending
        #     # the next one, instead of with a fixed delay as we do now
        #     await asyncio.sleep(0.05)
        #     print(f'sending image packet {index+1}/{len(printCommands)}')
        #     await self.send_packet(packet)

    def print_image(self, imgSrc):
        """ Print an image. """
        self.event_loop.run_until_complete(self._print_image(imgSrc))
    # async def run(self):
    #     async with BleakClient(self.address) as client:
    #         x = await client.is_connected()
    #         # logger.info("Connected: {0}".format(x))

    #         def btn_a_handler(sender, data):
    #             """Simple notification handler for btn a events."""
    #             print("{0}: {1}".format(sender, data))
    #             # Pick random letter to send
    #             if int.from_bytes(data, byteorder='little', signed=False) > 0:
    #                 letter = [randint(99, 122)]
    #                 self.event_loop.create_task(write_txt(letter))

    #         def btn_b_handler(sender, data):
    #             """Simple notification handler for btn b events."""
    #             print("{0}: {1}".format(sender, data))
    #             if int.from_bytes(data, byteorder='little', signed=False) > 0:
    #                 event_loop.create_task(client.disconnect())

    #         async def write_txt(data):
    #             await client.write_gatt_char(LED_TXT_UUID, data)

    #         await client.start_notify(BTN_A_UUID, btn_a_handler)
    #         await client.start_notify(BTN_B_UUID, btn_b_handler)

    #         while await client.is_connected():
    #             await asyncio.sleep(1)


# async def main():
#     instax = InstaxBle()
#     # instax.enable_printing()  # uncomment this line to enable actual printing
#     await instax.connect()
#     await instax.send_led_pattern(LedPatterns.pulseGreen)
#     await instax.print_image('example.jpg')
#     await instax.disconnect()
if __name__ == '__main__':
    instax = InstaxBle(address='FA:AB:BC:4E:20:CE', printerName=None, debug=True)
    try:  # make sure to use try except so we always disconnect
        # instax.connect()
        # print('call send_led_pattern')
        instax.send_led_pattern(LedPatterns.pulseGreen)  # see LedPatterns.py for some other options
        # sleep(2)
        # instax.send_led_pattern(LedPatterns.blinkBlue)
        # instax.wait(1.0)
        print('call print_image')
        instax.print_image('example.jpg')
        asyncio.run(asyncio.sleep(50.0))
        instax.disconnect()
    # sleep(5)
    # instax.disconnect()
    except KeyboardInterrupt:
        instax.disconnect()
    except Exception as e:
        print('Error: ', e)
        instax.disconnect()

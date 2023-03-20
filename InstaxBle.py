#!/usr/bin/env python3

from Types import EventType
from struct import pack, unpack_from
import LedPatterns
import simplepyble
import sys
from time import sleep
from math import ceil


class InstaxBle:
    def __init__(self, deviceAddress=None, printEnabled=False):
        """
        Initialize the InstaxBle class.
        deviceAddress: if specified, will only connect to a printer with this address.
        printEnabled: by default, actual printing is disabled to prevent misprints.
        """
        self.printEnabled = printEnabled
        self.peripheral = None
        self.deviceAddress = deviceAddress
        # self.service_uuid =
        # self.characteristic_uuid =
        self.serviceUUID = '70954782-2d83-473d-9e5f-81e1d02d5273'
        self.writeCharUUID = '70954783-2d83-473d-9e5f-81e1d02d5273'
        self.notifyCharUUID = '70954784-2d83-473d-9e5f-81e1d02d5273'
        self.packetsToSend = []
        self.waitingForResponse = False

        adapters = simplepyble.Adapter.get_adapters()
        if len(adapters) == 0:
            sys.exit("No bluetooth adapters found (are they enabled?)")
        if len(adapters) > 1:
            print(f"Found multiple adapters: {', '.join([adapter.identifier() for adapter in adapters])}")
            print(f"Using the first one: {adapters[0].identifier()}")
        self.adapter = adapters[0]

    def notification_handler(self, packet):
        # print('====================================')
        print('NOTIFICATION HANDLER')
        print(f'\t{packet}')
        print(f'\t{self.prettify_bytearray(packet)}')
        if len(packet) < 8:
            print(f"\tError: response packet size should be >= 8 (was {len(packet)})!")
        elif not self.validate_checksum(packet):
            print("\tChecksum validation error!")

        header, length, op1, op2 = unpack_from('<HHBB', packet)
        # print('\theader: ', header, '\t', self.prettify_bytearray(packet[0:2]))
        # print('\tlength: ', length, '\t', self.prettify_bytearray(packet[2:4]))
        # print('\top1: ', op1, '\t\t', self.prettify_bytearray(packet[4:5]))
        # print('\top2: ', op2, '\t\t', self.prettify_bytearray(packet[5:6]))

        # sleep(5)
        # if op1 == 16 and len(self.packetsToSend) > 0:
        #     print(f"notify: image data, packets left to send: {len(self.packetsToSend)}")
        #     print("go send next packet: ", self.packetsToSend[0], self.prettify_bytearray(self.packetsToSend[0]))
        #     nextPacket = self.packetsToSend.pop(0)
        #     self.send_packet(nextPacket)

        # else:
        try:
            event = EventType((op1, op2))
            print('\tevent: ', event)
        except Exception:
            print("\tUnknown event: ", (op1, op2))

        self.waitingForResponse = False
        # print('====================================')

        # if len(self.packetsToSend) > 0:
        #     self.send_packet(self.packetsToSend.pop(0))

        # # data = packet[4:-1]  # the packet without header and checksum
        # data = packet[6:-1]  # the packet without headers and checksum
        # print(f'Response data: {data} (length: {len(data)}, checksum OK)')
        # print(f'  {self.prettify_bytearray(data)}')

    def connect(self, timeout=0):
        """ Connect to the printer. Quit trying after timeout seconds. """
        # self.isConnected = False

        self.peripheral = self.find_device(timeout=timeout)
        if self.peripheral:
            try:
                print(f"\n\nConnecting to: {self.peripheral.identifier()} [{self.peripheral.address()}]")
                self.peripheral.connect()
                if self.peripheral.is_connected():
                    print("Connected!")
                    print('mtu: ', self.peripheral.mtu())

                    # self.isConnected = True
                # print(dir(self.peripheral))
                # self.client.start_notify(self.notifyUUID, self.notification_handler)
                # self.peripheral.notify(self.notifyUUID, self.notification_handler)
                # peripheral.write_command(service_uuid, characteristic_uuid, str.encode(content))
                print('attach notification_handler')
                self.peripheral.notify(self.serviceUUID, self.notifyCharUUID, self.notification_handler)
                print('done')

            except Exception as e:
                print('error on attaching notification_handler: ', e)

        # self.peripheral.connect()
        # self.peripheral.notify(self.notifyUUID, self.notification_handler)
        # self.peripheral.notify(service_uuid, characteristic_uuid, notification_handler)

    def disconnect(self):
        if self.peripheral:
            self.peripheral.disconnect()

    def enable_printing(self):
        """ Enable printing. """
        self.printEnabled = True

    def disable_printing(self):
        """ Disable printing. """
        self.printEnabled = False

    def find_device(self, timeout=0):
        """" Scan for our device and return it when found """
        print('Looking for instax printer...')
        secondsTried = 0
        while True:
            self.adapter.scan_for(2000)
            peripherals = self.adapter.scan_get_results()
            for peripheral in peripherals:
                foundName = peripheral.identifier()
                foundAddress = peripheral.address()
                print(f"Found: {foundName} [{foundAddress}]")
                if (self.deviceAddress is None and foundName.startswith('INSTAX-')) or \
                   foundAddress == self.deviceAddress:
                    if foundAddress.startswith('FA:AB:BC'):  # found the IOS endpoint, convert to ANDROID endpoint
                        # foundName = foundName.replace('IOS', 'ANDROID')
                        # foundAddress = foundAddress.replace('FA:AB:BC', '88:B4:36')
                        if peripheral.is_connectable():
                            return peripheral
                        else:
                            print(f"Printer at {foundAddress} is not connectable")
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
        self.send_packet(packet)

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

    def send_packet(self, packet, isDataPacket=False):
        """ Send a packet to the printer. """
        # print('------------------------------------------------------------')
        if not self.peripheral:
            print("no peripheral to send packet to")
        if not self.peripheral.is_connected():
            print("peripheral not connected")
        # self.peripheral.write_command(self.writeCharUUID, packet)
        # print('sending, MTU: ', self.peripheral.mtu())
        # print('sending: ', type(packet), packet[0:40])
        header, length, op1, op2 = unpack_from('<HHBB', packet)

        # sleep(5)
        # if op1 == 16 and len(self.packetsToSend) > 0:
        #     print(f"notify: image data, packets left to send: {len(self.packetsToSend)}")
        #     print("go send next packet: ", self.packetsToSend[0], self.prettify_bytearray(self.packetsToSend[0]))
        #     nextPacket = self.packetsToSend.pop(0)
        #     self.send_packet(nextPacket)

        # else:
        event = 'Unknown event'
        try:
            event = EventType((op1, op2))
        except Exception:
            if isDataPacket:
                event = 'Image data'
            pass

        if not isDataPacket:
            self.waitingForResponse = True

        print('sending: ', event, self.prettify_bytearray(packet[0:30]))
        self.peripheral.write_command(self.serviceUUID, self.writeCharUUID, packet)

        if isDataPacket:
            print('don\'t wait for response, continue')
            pass
        else:
            print('message send, wait for response...')
            while self.waitingForResponse:
                sleep(0.1)
            # print('response received, continue')
        # print('------------------------------------------------------------')
        # else:
        #     print('sending write_request:')
        #     print(self.peripheral.write_request(self.serviceUUID, self.writeCharUUID, packet))
        # self.peripheral.write_command(self.serviceUUID, self.writeCharUUID, packet)

    # TODO: printer doesn't seem to respond to this
    # async def shut_down(self):
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
        """
        print an image. Either pass a path to an image (as a string) or pass
        the bytearray to print directly
        """
        imgData = imgSrc
        if isinstance(imgSrc, str):  # if it's a path, load the image contents
            imgData = self.image_to_bytes(imgSrc)

        packetsToSend = [(
            self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_START, b'\x02\x00\x00\x00\x00\x00' + pack('>H', len(imgData))),
            False
        )]
        # print('MTU: ', self.peripheral.mtu())
        # exit()

        # divide image data up into chunks of 900 bytes and pad the last chunk with 0s if needed
        imgDataChunks = [imgData[i:i + 900] for i in range(0, len(imgData), 900)]
        if len(imgDataChunks[-1]) < 900:
            imgDataChunks[-1] = imgDataChunks[-1] + bytes(900 - len(imgDataChunks[-1]))

        for index, chunk in enumerate(imgDataChunks):
            imgDataChunks[index] = pack('>I', index) + chunk  # add chunk number as int (4 bytes)

            chunkPacket = self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_DATA, imgDataChunks[index])
            # print(chunkPacket)
            for subPartIndex in range(ceil(len(chunkPacket) / 182)):
                subPacket = chunkPacket[subPartIndex * 182:subPartIndex * 182 + 182]
                if len(subPacket) == 0:
                    break
                if len(subPacket) < 182:
                    subPacket = subPacket + bytes(182 - len(subPacket))
                packetsToSend.append((
                    subPacket,
                    (subPartIndex != 9)
                ))
            # packetsToSend.append((
            #     self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_DATA, imgDataChunks[index]),
            #     False
            # ))

        packetsToSend.append((
            self.create_packet(EventType.PRINT_IMAGE_DOWNLOAD_END),
            False
        ))

        if self.printEnabled:
            packetsToSend.append((
                self.create_packet(EventType.PRINT_IMAGE),
                False
            ))
            packetsToSend.append((
                self.create_packet((0, 2), b'\x02'),
                False
            ))
        else:
            print("Printing is disabled, sending all packets except the actual print command")

        # manually send the start signal, after this the notify_handler will send the rest
        while len(packetsToSend) > 0:
            nextPacket = packetsToSend.pop(0)
            self.send_packet(nextPacket[0], nextPacket[1])
            while self.waitingForResponse:
                sleep(.1)
        print("all image data sent")
        sleep(1)  # allow the printer to respond to the last packet of our image

    def print_services(self):
        print("Successfully connected, listing services...")
        services = self.peripheral.services()
        service_characteristic_pair = []
        for service in services:
            for characteristic in service.characteristics():
                service_characteristic_pair.append((service.uuid(), characteristic.uuid()))

        for i, (service_uuid, characteristic) in enumerate(service_characteristic_pair):
            print(f"{i}: {service_uuid} {characteristic}")


instax = None


def main():
    global instax
    # instax = InstaxBle(deviceAddress='88:B4:36:4E:20:CE')
    instax = InstaxBle(deviceAddress='FA:AB:BC:4E:20:CE')
    instax.enable_printing()  # uncomment this line to enable actual printing
    instax.connect()
    # print("Successfully connected, listing services...")
    # instax.print_services()
    # instax.send_led_pattern(LedPatterns.blinkBlue)
    # while instax.waitingForResponse:
    #     sleep(5)
    # instax.send_led_pattern(LedPatterns.pulseGreen)
    # while instax.waitingForResponse:
    #     sleep(5)
    # instax.send_led_pattern(LedPatterns.blinkRGB)
    # while instax.waitingForResponse:
    #     sleep(5)
    # instax.print_services()
    # instax.print_image('example.jpg')
    instax.print_image('moos.jpeg')
    instax.disconnect()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
import socket
import asyncio
from Types import EventType, InfoType
from struct import unpack_from
from bluetooth import discover_devices


class InstaxLinux:
    def __init__(self):
        self.sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

    def connect(self, timeout=0):
        """ Connect to the printer. Quit trying after timeout seconds. """
        self.isConnected = False
        if self.deviceAddress is None:
            self.device = self.find_device(timeout=timeout)
            if self.device:
                print(f'found device {self.device.name}, connecting...')
                self.deviceAddress = self.device.address
            else:
                print('no device found')
                exit()

        try:
            print(f'connecting to device {self.deviceAddress}')
            self.sock.connect((self.deviceAddress, 6))
            self.isConnected = True
            print('connected')
        except Exception as e:
            print(f'connection failed: {e}')

    def find_device(self, timeout=0):
        """" Scan for our device and return it if found """
        print('Looking for instax printer...')
        secondsTried = 0
        while True:
            devices = discover_devices(lookup_names=True, duration=1)
            for foundName, foundAddress in devices:
                if (self.deviceName is None and foundName.startswith('INSTAX-')) or \
                   foundName == self.deviceName or foundAddress == self.deviceAddress:
                    if foundName.startswith('FA:AB:BC'):  # found the IOS endpoint, convert to ANDROID endpoint
                        foundName = foundName.replace('IOS', 'ANDROID')
                        foundAddress = foundAddress.replace('FA:AB:BC', '88:B4:36')
                    device = {
                        'name': foundName,
                        'address': foundAddress,
                    }
                    return device
            secondsTried += 1
            if timeout != 0 and secondsTried >= timeout:
                return None

    def close(self):
        """
            Close the connection to the printer.
            TODO: not sure if we actualy need to use this
        """
        if self.isConnected:
            self.sock.close()

    def send_packet(self, packet):
        """
        Send a passed packet to the printer.
        Returns: the server's response.
        """
        # print("sending: ", self.prettify_bytearray(packet))
        if self.isConnected:
            self.sock.send(packet)
            response = self.sock.recv(64)
            # self.sock.close()
            return response

    def parse_response(self, response):
        """
        Takes a response from the printer and handles it based on
        the returned type
        """
        header, length, op1, op2 = unpack_from('>HHBB', response)
        if (op1, op2) == EventType.XYZ_AXIS_INFO.value:
            x, y, z, o = unpack_from('<hhhB', response[6:-1])
            print(f'x: {x}, y: {y}, z: {z}, o: {o}')
            return
        elif (op1, op2) == EventType.SUPPORT_FUNCTION_INFO.value:
            infoType = InfoType(response[6])
            if infoType == InfoType.BATTERY_INFO:
                self.batteryState, self.batteryPercentage = unpack_from('>BB', response[8:10])
                print(f'battery state: {self.batteryState}, battery percentage: {self.batteryPercentage}')
                return
            elif infoType == InfoType.PRINTER_FUNCTION_INFO:
                dataByte = response[8]
                self.photosLeft = dataByte & 15
                self.isCharging = (1 << 7) & dataByte >= 1
                print(f'photos left: {self.photosLeft}, is charging: {self.isCharging}')
                return

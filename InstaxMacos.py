#!/usr/bin/env python3

from Types import EventType, InfoType
from struct import pack, unpack_from
import asyncio
from bleak import BleakScanner, BleakClient


class InstaxMacos:
    def __init__(self):
        self.writeUUID = '70954783-2d83-473d-9e5f-81e1d02d5273'
        self.notifyUUID = '70954784-2d83-473d-9e5f-81e1d02d5273'
        self.client = BleakClient(None)

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

    async def connect(self, timeout=0):
        """ Connect to the printer. Quit trying after timeout seconds. """
        self.device = await self.find_device(timeout=timeout)
        if self.device:
            try:
                self.client = BleakClient(self.device.address)
                if not self.client.is_connected:
                    await self.client.connect()
                await self.client.start_notify(self.notifyUUID, self.notification_handler)
            except Exception as e:
                print('error on attaching notification_handler: ', e)

    def send_packet(self, packet):
        if self.client:
            if not self.client.is_connected:
                await self.client.connect()
            await self.client.write_gatt_char(self.writeUUID, packet)
        else:
            print("no client to send packet to")

    def find_device(self, response):
        raise NotImplementedError("find_device not implemented for MacOS yet")

    def parse_response(self, response):
        raise NotImplementedError("parse_response not implemented for MacOS yet")

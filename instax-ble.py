#!/usr/bin/env python3

import asyncio
import socket

from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from struct import pack, unpack_from
from events import EventType
import parsers
from time import sleep
import logging
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

writeUUID = '70954783-2d83-473d-9e5f-81e1d02d5273'
notifyUUID = '70954784-2d83-473d-9e5f-81e1d02d5273'

def prettify_bytearray(value):
    return ' '.join([f'{x:02x}' for x in value])

# data = b'aB\x00\x0f0\x00\x00\x03\xe0\xff\xe0\x00\x10\x00K'
# parseAccelerometer(data)
# print(prettify_bytearray(data))  # header

# header, length, i, k, x, y, z, o = unpack_from('<HHBBhhhB', data)
# _logger.info(f' header: {header} \t{prettify_bytearray(data[0:2])}')
# _logger.info(f' length: {length} \t{prettify_bytearray(data[2:4])}')
# _logger.info(f' i: {i} \t\t{prettify_bytearray(data[4:5])}')
# _logger.info(f' k: {k} \t\t{prettify_bytearray(data[5:6])}')
# _logger.info(f' x: {x} \t\t{prettify_bytearray(data[6:8])}')
# _logger.info(f' y: {y} \t\t{prettify_bytearray(data[8:10])}')
# _logger.info(f' z: {z} \t\t{prettify_bytearray(data[10:12])}')
# _logger.info(f' o: {o} \t\t{prettify_bytearray(data[12:13])}')

def createChecksum(bytearray: bytearray):
    return (255 - (sum(bytearray) & 255)) & 255;

def createPacket(eventType, payload:bytes=b''):
    # for easier debugging as this allow to pass the enum value directly as well
    if isinstance(eventType, EventType):
        eventType = eventType.value

    header = b'\x41\x62'  # 'Ab' from client to printer, 'aB' from printer to client
    opCode = bytes([eventType[0], eventType[1]])
    packetSize = pack('>H', 7 + len(payload))
    packet = header + packetSize + opCode + payload
    packet += pack('B', createChecksum(packet))
    _logger.info(f"Sending packet: {packet}, (length: {len(packet)})")
    _logger.info(f"  {prettify_bytearray(packet)} (length: {len(packet)})")
    return packet

def validate_checksum(data):
    return (sum(data) & 255) == 255

def notification_handler(characteristic: BleakGATTCharacteristic, packet: bytearray):
    if len(packet) < 8:
        _logger.error(f"Error: response packet size should be >= 8 (was {len(packet)})")
        return
    elif not validate_checksum(packet):
        _logger.error("Checksum validation failed")
        return

    header, length, op1, op2 = unpack_from('>HHBB', packet)
    _logger.info(f'header: {header}\t{prettify_bytearray(packet[0:2])}')
    _logger.info(f'length: {length}\t{prettify_bytearray(packet[2:4])}')
    _logger.info(f'op1: {op1}\t\t{prettify_bytearray(packet[4:5])}')
    _logger.info(f'op2: {op2}\t\t{prettify_bytearray(packet[5:6])}')
    try:
        eventType = EventType((op1, op2))
    except ValueError:
        _logger.error(f"Unknown event type ({op1}, {op2}")
        return

    _logger.info(f"eventType: {eventType}")
    data = packet[6:-1]  # the packet without headers, opcodes and checksum
    _logger.info(f'response data: {data} (length: {len(data)}, checksum OK)')
    _logger.info(f'  {prettify_bytearray(data)}')

    match eventType:
        case EventType.XYZ_AXIS_INFO:
            parsers.XYZ_AXIS_INFO(data)
        case EventType.DEVICE_INFO_SERVICE:
            parsers.DEVICE_INFO_SERVICE(data)
        case _:
            _logger.info(f"No parser for event type {eventType}")

def createColorPayload(colorArray, speed=5, loop=0, when=0):
    # loop is value - 1 , so 0 = play once, 1 = play twice. 255 == repeat infinitly
    # when: 0 = normal, 1 = on print, 2 = on print completion, 3 = pattern switch
    payload = pack('BBBB', when, len(colorArray), speed, loop)
    for color in colorArray:
        payload += pack('BBB', color[0], color[1], color[2])
    return payload

async def find_device(mode='ANDROID'):
    """" Scan for our device and return it when found """
    dev = None
    while True:
        devices = await BleakScanner.discover(timeout=2)
        for d in devices:
            if d.name.startswith('INSTAX-') and d.name.endswith(f'({mode})'):
                dev = d
                break
        if dev:
            break
    return dev


async def main():
    dev = await find_device()

    print(f'Found instax printer {dev.name} at {dev.address}')
    async with BleakClient(dev.address) as client:
        print('connected')
        await client.start_notify(notifyUUID, notification_handler)

        packet = createPacket(EventType.DEVICE_INFO_SERVICE, b'\x02')  # get serialnumber
        await client.write_gatt_char(writeUUID, packet)
        await asyncio.sleep(1.0)

        packet = createPacket(EventType.XYZ_AXIS_INFO)  # get accelerometer info
        while True:
            await client.write_gatt_char(writeUUID, packet)
            await asyncio.sleep(0.5)


async def sendColor():
    """ send a color pattern """
    dev = await find_device()
    payload = createColorPayload([[255, 0, 0], [255, 255, 255]], 40, 255)
    packet = createPacket(EventType.LED_PATTERN_SETTINGS, payload)

    sock=socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    print('socket created')
    sock.connect((dev.address, 6))
    print('socket connected')
    sock.send(packet)
    resp = sock.recv(8)
    sock.close()
    return resp


def print_translation_list():
    """ Helper function to print a list of all possible byte values and their translations"""
    for x in range(0, 256):
        print(f'int: {x}, hex: {x:02x}, bytes: {bytes([x])}')

if __name__ == '__main__':
    # asyncio.run(main())
    # print_translation_list()
    asyncio.run(sendColor())

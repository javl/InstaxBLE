#!/usr/bin/env python3

import asyncio

from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from struct import pack, unpack_from
from events import EventType
import parsers

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

def createPacket(eventType: EventType, payload:bytes=b''):
    header = b'\x41\x62'  # 'Ab' from client to printer, 'aB' from printer to client
    opCode = bytes([eventType.value[0], eventType.value[1]])
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
            print('at XYZ_AXIS_INFO')
        case EventType.DEVICE_INFO_SERVICE:
            parsers.DEVICE_INFO_SERVICE(data)
        case _:
            _logger.info(f"No parser for event type {eventType}")

async def main():
    dev = None
    devices = await BleakScanner.discover()
    for d in devices:
        if d.name.startswith('INSTAX-')  and d.name.endswith('(IOS)'):
            dev = d
            break
    if not dev:
        _logger.error("No printer found")
        exit()

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

asyncio.run(main())

#!/usr/bin/env python3

import asyncio
import socket
from PIL import Image
from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from struct import pack, unpack_from
from events import EventType
import parsers
from time import sleep
from math import ceil
from PIL import Image
from struct import pack

import logging
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

writeUUID = '70954783-2d83-473d-9e5f-81e1d02d5273'
notifyUUID = '70954784-2d83-473d-9e5f-81e1d02d5273'
imageBytes = b''
imageBytesLength = 0

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
    # _logger.info(f"Sending packet: {packet}, (length: {len(packet)})")
    # _logger.info(f"  {prettify_bytearray(packet)} (length: {len(packet)})")
    return packet

def validate_checksum(data):
    return (sum(data) & 255) == 255


def handleIncomingPacket(packet):
    global imageBytes
    global imageBytesLength
    # if len(packet) < 8:
    #     _logger.error(f"Error: response packet size should be >= 8 (was {len(packet)})")
    #     return
    # elif not validate_checksum(packet):
    #     _logger.error("Checksum validation failed")
    #     return
    if not validate_checksum(packet):
        _logger.error("Checksum validation failed")
        # print((prettify_bytearray(packet)))
        # return

    header, length, op1, op2 = unpack_from('>HHBB', packet)
    # _logger.info(f'header: {header}\t{prettify_bytearray(packet[0:2])}')
    # _logger.info(f'length: {length}\t{prettify_bytearray(packet[2:4])}')
    # _logger.info(f'op1: {op1}\t\t{prettify_bytearray(packet[4:5])}')
    # _logger.info(f'op2: {op2}\t\t{prettify_bytearray(packet[5:6])}')
    try:
        eventType = EventType((op1, op2))
    except ValueError:
        _logger.error(f"Unknown event type ({op1}, {op2}")
        return

    # _logger.info(f"eventType: {eventType}")
    data = packet[6:-1]  # the packet without headers, opcodes and checksum
    # _logger.info(f'response data: {data} (length: {len(data)}, checksum OK)')
    # _logger.info(f'  {prettify_bytearray(data)}')

    match eventType:
        case EventType.XYZ_AXIS_INFO:
            parsers.XYZ_AXIS_INFO(data)
        case EventType.DEVICE_INFO_SERVICE:
            parsers.DEVICE_INFO_SERVICE(data)
        case EventType.PRINT_IMAGE_DOWNLOAD_START:
            # imageBytes = parsers.PRINT_IMAGE_DOWNLOAD_START(data)
            print(prettify_bytearray(packet))
            print('                 ', prettify_bytearray(data))
            pictureType, printOption, doubleDensity, unused, imageBytesLength = unpack_from('>BBBBI', data)
            print('pictureType: ', pictureType)
            print('printOption: ', printOption)
            print('doubleDensity: ', doubleDensity)
            print('unused: ', unused)
            print('total imageBytesLength: ', imageBytesLength)
            print('imageBytesLength: ', imageBytesLength)
            # imageBytes = data[8:]
            imageBytes = b''
        case EventType.PRINT_IMAGE:
            print("data: ", data)
            print(prettify_bytearray(packet))
            # framenumber = unpack_from('>I', data)
            # print('data  frameNumber: ', framenumber)
            # imageBytes += data[4:]
            # print('here')
            # imageBytes += parsers.PRINT_IMAGE_DOWNLOAD_START(data)
        case EventType.PRINT_IMAGE_DOWNLOAD_DATA:
            frameNumber = unpack_from('>I', data)
            # print('data  frameNumber: ', framenumber)
            imageBytes += data[4:]
            # print('here')
            # imageBytes += parsers.PRINT_IMAGE_DOWNLOAD_START(data)
        case EventType.PRINT_IMAGE_DOWNLOAD_END:
            # print('img len: ', len(imageBytes))
            # parsers.PRINT_IMAGE_DOWNLOAD_END(imageBytes)
            # print('A last 20', imageBytes[-20:])
            # print('total: ', len(imageBytes))
            # last_value = len(imageBytes) - 1
            # for x in range(len(imageBytes)-1, -1, -1):
            #     # print(x)
            #     if imageBytes[x] == 0:
            #         last_value = x
            #     else:
            #         break
            imageBytes = imageBytes[0:imageBytesLength]
            print('final len: ', len(imageBytes))
            with open("output.jpg", "wb") as binary_file:
                binary_file.write(imageBytes)

            # print(prettify_bytearray(imageBytes))

        case EventType.SUPPORT_FUNCTION_INFO:
            pass
        case _:
            _logger.info(f"No parser for event type {eventType}")
            # exit()

def notification_handler(characteristic: BleakGATTCharacteristic, packet: bytearray):
  handleIncomingPacket(packet)

def createColorPayload(colorArray, speed=5, loop=0, when=0):
    # loop is value - 1 , so 0 = play once, 1 = play twice. 255 == repeat forever
    # when: 0 = normal, 1 = on print, 2 = on print completion, 3 = pattern switch
    payload = pack('BBBB', when, len(colorArray), speed, loop)
    for color in colorArray:
        payload += pack('BBB', color[0], color[1], color[2])
    return payload

async def find_device(mode='ANDROID'):
    """" Scan for our device and return it when found """
    print('Look for instax printer...')
    dev = None
    while True:
        devices = await BleakScanner.discover(timeout=2)
        for d in devices:
            if d.name.startswith('INSTAX-') and d.name.endswith(f'({mode})'):
                dev = d
                break
        if dev:
            break
        print('.', end='')
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

    im = Image.open('gradient.jpg')
    px = im.load()
    size = im.size if im._getexif().get(274,0) < 5 else im.size[::-1]
    colorArray = []
    for x in range(0, size[0], 20):
        color = im.getpixel((x, 0))
        colorArray.append([color[0], color[1], color[2]])

    payload = createColorPayload(colorArray, 10, 255)
    print(payload)
    packet = createPacket(EventType.LED_PATTERN_SETTINGS, payload)

    sock=socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    print('socket created')
    sock.connect((dev.address, 6))
    print('socket connected')
    sock.send(packet)
    resp = sock.recv(8)
    sock.close()
    return resp

async def printImage():
    """ print an image """
    dev = await find_device()
    global imageBytesLength

    # payload = pack('>BBBBI', 2, 0, 0, 0, 0) + imageToBytes()
    # packet = createPacket(EventType.PRINT_IMAGE_DOWNLOAD_DATA, payload)

    imgData = imageToBytes('test_noexif.jpg')
    numberOfChunks = ceil(len(imgData) / 900)
    printCommands = [
        # createPacket(EventType.PRINT_IMAGE_DOWNLOAD_START, b'\x02\x00\x00\x00\x00\x00' + pack('>H', numberOfChunks * 900))
        createPacket(EventType.PRINT_IMAGE_DOWNLOAD_START, b'\x02\x00\x00\x00\x00\x00' + pack('>H', len(imgData)))
    ]
    # divide up into chunks of 900 bytes
    imgDataChunks = [imgData[i:i+900] for i in range(0, len(imgData), 900)]
    if len(imgDataChunks[-1]) < 900:
        imgDataChunks[-1] = imgDataChunks[-1] + bytes(900 - len(imgDataChunks[-1]))

    for index, chunk in enumerate(imgDataChunks):
        imgDataChunks[index] = pack('>I', index) + chunk  # add chunk number as int (4 bytes)
        printCommands.append(createPacket(EventType.PRINT_IMAGE_DOWNLOAD_DATA, pack('>I', index) + chunk))
        # print('size: ', len(imgDataChunks[index]))

    # startCommand = b'\x41\x62\x00\x0f\x10\x00\x02\x00\x00\x00\x00\x00\xc7\x4d\x27'
    # printCommands.extend(imgDataChunks)
    printCommands.extend([
        createPacket(EventType.PRINT_IMAGE_DOWNLOAD_END),
        # createPacket(EventType.IDENTIFY_INFORMATION, b'\x02'),
        # createPacket((0, 2), b'\x02'),
        createPacket(EventType.PRINT_IMAGE),
        createPacket((0, 2), b'\x02'),
        createPacket((0, 2), b'\x02'),
        createPacket((0, 2), b'\x02'),
        createPacket((0, 2), b'\x02'),
        createPacket((0, 2), b'\x02'),

        # 61 42 00 11 00 02 00 02 38 00 00 0f 00 00 00 00 00
        # 61 42 00 11 00 02 00 02 26 00 00 10 00 00 00 00 11"


        # createPacket(EventType.IDENTIFY_INFORMATION, b'\x02'),
        # createPacket(EventType.PRINT_IMAGE,
        # b'\x41\x62\x00\x07\x10\x02\x43', # print image
        # b'\x41\x62\x00\x08\x00\x02\x02\x50',
        # b'\x41\x62\x00\x07\x10\x02\x43', # print image
        # b'\x41\x62\x00\x08\x00\x02\x02\x50',

        # b'\x41\x62\x00\x07\x10\x02\x43',
        # b'\x41\x62\x00\x08\x00\x02\x02\x50',
        # b'\x41\x62\x00\x07\x10\x02\x43',
        # b'\x41\x62\x00\x08\x00\x02\x02\x50',
    ])
    print('mineA: ', prettify_bytearray(printCommands[0]))
    print('mineB: ', prettify_bytearray(printCommands[1])[:100])
    print('mineC: ', prettify_bytearray(printCommands[2])[:100])
    print('mineD: ', prettify_bytearray(printCommands[3])[:100])
    print('mineE: ', prettify_bytearray(printCommands[4])[:100])
    print('mineF: ', prettify_bytearray(printCommands[5])[:100])
    print()
    # return

    for index, f in enumerate(printCommands):
        if not validate_checksum(f):
            print(index, 'checksum error on command', prettify_bytearray(f))
            exit()


    # return
    # print('frames = [')
    # for x in printCommands:
    #     print(x, ',')
    # print(']')
    # exit()
    # printCommands.append(b'\x41\x62\x00\x07\x10\x80\xc5') # print image

    # if len(printCommands) != len(frames):
    #     print("ERROR: frames and printCommands don't match")
    #     exit()

    # for x in range(0, len(printCommands)):
    # #     # print('orig: ', prettify_bytearray(frames[x][:40]))
    # #     # print('mine: ', prettify_bytearray(printCommands[x][:40]))
    #     if frames[x] != printCommands[x]:
    #         print(f"commands at {x} don't match:")
    #         print('mine: ', prettify_bytearray(printCommands[x][:40]))
    #         print('orig: ', prettify_bytearray(frames[x][:40]))
    #         print('')

    # for index, x in enumerate(frames):
    #     print(index, x[:40])

    # print('orig: ', prettify_bytearray(frames[0]))
    # print('mine: ', prettify_bytearray(stuff_to_send[0]))
    # exit()

    sock=socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    sock.connect((dev.address, 6))
    print('socket connected')
    for index, packet in enumerate(printCommands):
        # sleep(0.05)
        print(f'sending packet {index+1}/{len(printCommands)}')
        print(f'({len(packet)}) {prettify_bytearray(packet[:40])}')
        sock.send(packet)
        # print('wait for response')
        resp = sock.recv(64)
        # print(len(resp))
        print('resp: ', prettify_bytearray(resp), 'valid checksum: ', validate_checksum(resp))
    sock.close()
    return resp


def print_translation_list():
    """ Helper function to print a list of all possible byte values and their translations"""
    for x in range(0, 256):
        print(f'int: {x}, hex: {x:02x}, bytes: {bytes([x])}')

def imageToBytes(filename):
    imgdata = None

    # strip all metadata
    # image = Image.open('test_.jpg')
    # data = list(image.getdata())
    # image_without_exif = Image.new(image.mode, image.size)
    # image_without_exif.putdata(data)
    # image_without_exif.save('test_noexif.jpg')

    # with open("test_noexif.jpg", "rb") as image:
    with open(filename, "rb") as image:
        imgdata = bytearray(image.read())
    return imgdata

# announce sending
# img_start = b'\x41\x62\x00\x0f\x10\x00\x02\x00\x00\x00\x00\x00\xdb\xb2\xae\x53'
# send image data
# announce end of file
# img_end =   b'\x41\x62\x00\x07\x10\x02\x43\x53'

# from framesC2 import *
from framesGirl import *

if __name__ == '__main__':
    # asyncio.run(main())
    # print_translation_list()
    asyncio.run(sendColor())
    # asyncio.run(printImage())

    # girl_frame_1 = b'Ab\x03\x8f\x10\x01\x00\x00\x00\x00\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x06\x04\x05\x06\x05\x04\x06\x06\x05\x06\x07\x07\x06\x08\n\x10\n\n\t\t\n\x14\x0e\x0f\x0c\x10\x17\x14\x18\x18\x17\x14\x16\x16\x1a\x1d%\x1f\x1a\x1b#\x1c\x16\x16 , #&\')*)\x19\x1f-0-(0%()(\xff\xdb\x00C\x01\x07\x07\x07\n\x08\n\x13\n\n\x13(\x1a\x16\x1a((((((((((((((((((((((((((((((((((((((((((((((((((\xff\xc0\x00\x11\x08\x03 \x02X\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1d\x00\x00\x01\x05\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x02\x03\x05\x06\x01\x07\x08\t\xff\xc4\x00<\x10\x00\x01\x04\x02\x01\x03\x03\x03\x03\x04\x02\x01\x04\x01\x02\x07\x01\x00\x02\x03\x11\x04!1\x05\x12A\x13"Q\x06aq\x142\x81#B\x91\xa1\x07\xb1R\x15$3\xc1\xe1\x16r\xd1\xf04bC\x92\xf1\xff\xc4\x00\x1b\x01\x00\x03\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x00\x04\x05\x06\x07\xff\xc4\x00(\x11\x00\x02\x02\x02\x02\x02\x03\x00\x02\x03\x01\x01\x01\x00\x00\x00\x00\x01\x02\x11\x03!\x121\x04A\x13"Q\x05a2Bq\x14\x15R\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xd6\xba*y\xd1\xaf\x954-i?u;\x98\t\xda\x8d\xcd\xedp\xab\\\xf1|Q\xca\xe3L6\x18\xc0\xe0\xa7\x92\x08#\x7f\x95\x14/:\xbe\x11\x0cm\xd84\x12\xb9\x96\x88;\x9an\xd3\xcb\xa8r\xa4p\xae\x02\x1eGr6\x97\xd1A\xfd\xe3\xe6\xd7\ti\x07V\x87\xee\xed\x07Ew\xd4\xee48\xa5&\x16G3Z\x0f\x08y\x1d@\x80-\x14[c\xe5F\xf8I\xd5%\xda\x11\x95\xf2\x0b;B\xca\xd2\x01\x03AZK\x8fTO(WGd\xd2\xa4d\xd0\x8dX\x14l\xa2@\x00\xedY\xe37\xb4s\xb4\xb1\xe0kF\xc6\xd1-\x88\xf8\x01]N\x90\xd1\x8d\x0e\x8f\xd8\xbb,\x84\x0bR5\xb4\xdb\xaf\xca\x1f!\xc4\x829R\x94\xa8v\xf4\t$\x96H\xe0\xaeU\xd2u\x0e\xe2\x08\xb4\xe6\xb7{\xe5.%\xc9\x90\x938\xd6\x1f\x07\x80\xa5h$]\x7f\x84\xa8\xb4\xd0\xd1]\x0e#\xc5.\xe5\x04\x96\x89\x8e\xee\xe0\x0b\x1bD\xc7 \r\x1a\xb4\x1b\x9e\xd2o\x87yO\x89\xc2\xb9U\x83\xa0Xhwq\xad\xa7\xf6\x80E\xa8\x19!\nF\x9b\xd9\xb5\xd1\xaa\xd8\xcbg$`\xb2HB\xb9\xa2\xc8\xff\x00\x08\xb2\xde\xeb\xd6\xbeT24\x81@U)K\x1cXn\x88\x08!M\x13\xe8n\xd2lw\xee\x04\xda\xeb\x98hx\\\xee4\x14\xc9\x1a\xe0G\xc1\xf8N\x07txQP\xb1\xe5<\x11j\x13ES\x1c\xd0(\xf3K\xa7\xec\x95\x1a\xa0\x96\xfb\xb46\xb8\xe5\x16\x98\xd64\x82M\xae\xe8\x8f+\xaen\x82kA:\xf8Y\x04{\x1eO\x91\xf8R\x03i\x81\xa3\x91\xcasEo\xca6\x14\x84Z>\x14W\xbd)\xaf\xc9Q\xb9\xbe\xe2\x7f\xd2F\x8c\xd0\x81\xdd\xa7\xc6\xf3f\xf8Q\xb4oi\xcd\x00\x1d\xd1V\xc7*\'V\x10\xd9\xfbv6\xd4\xe7N]\xf2\x10\xd4\x1c\xefi\\\xe0\x9b:]q\xcc\xd0\x1cI\x9c\xe2v\x99\xdff\x82ip \x01\xc7\xe5F\xf7\x0693\x9b\x90\x12\xa0\xb6\x9a\xfc\xa9;\x89\x08x\x8e\xac\xf0T\xbd\xd4\x97\x88[:\xe2\xb8\x1b{O\x0fi\xf8]\x04\x13\xed\x1aJ\xe0\x0eDm\x03\xb8\xa5\xa1i\xd2P \xa6\x9d\x1f\xb9\xe4.y7\x165\x1d\xb3_d\xfa\xbe\xd51'
    # print('girlA: ', prettify_bytearray(frames[0]))
    # print('girlB: ', prettify_bytearray(frames[1])[:100])
    # print('girlC: ', prettify_bytearray(frames[2])[:100])
    # print('girlD: ', prettify_bytearray(frames[3])[:100])
    # print('girlE: ', prettify_bytearray(frames[4])[:100])
    # print('girlF: ', prettify_bytearray(frames[5])[:100])
    # 41 62 03 8f 10 01 00 00 00 00 ff d8 ff e0 00 10 4a 46 49 46 00 01 01 00 00 01 00 01
    # 41 62 03 8b 10 01 ff d8 ff e0 00 10 4a 46 49 46 00 01 01 00 00 01 00 01 00 00 ff db 00 43

    # girl = b'Ab\x00\x0f\x10\x00\x02\x00\x00\x00\x00\x00\xc8d\x0f'
    # print(unpack_from('>HHBBBBBBBBHB', girl))
    # print('1: ')
    # data = b'\x41\x62\x00\x0f\x10\x00\x02\x00\x00\x00\x00\x00\xc7\x4d\x27'
    # print(unpack_from('>HHBBBBBBBBHB', data))
    # header, length, op1, op2 = unpack_from('>HHBB', data)
    # print('header: ', header)
    # print('length: ', length)
    # print('op1: ', op1)
    # print('op2: ', op2)
    # print(unpack_from('>HHBB', data))

    # print('2: ')
    # data = b'\x41\x62'
    # print(unpack_from('<BB', data))

    # print('3: ')
    # data = b'Ab'
    # print(unpack_from('<BB', data))

    # print('4: ')
    # data = b'Ab\x00\x0f0\x00\x00\x03\xe0\xff\xe0\x00\x10\x00K'
    # print(unpack_from('<BBHBBhhhB', data))

    # print('num frames: ', len(frames))


    # data = frames[0]
    # header, length, op1, op2 = unpack_from('>HHBB', data)
    # print('header: ', header)
    # print('length: ', length)
    # print('op1: ', op1)
    # print('op2: ', op2)
    # # print(unpack_from('>HHBB', data))
    # print(unpack_from('>HHBBBBBBBBHB', data))

    # for x in frames:
    #     packet = bytes(x)
    #     header, length, op1, op2 = unpack_from('>HHBB', packet)
    #     # print('header: ', header)
    #     handleIncomingPacket(packet)
    #     # print(len(packet))
    # print(prettify_bytearray(frames[-1]))

import asyncio

from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from struct import pack, unpack_from

writeUUID = '70954783-2d83-473d-9e5f-81e1d02d5273'
notifyUUID = '70954784-2d83-473d-9e5f-81e1d02d5273'

def prettify_bytearray(value):
  return ' '.join([f'{x:02x}' for x in value])

def parseAccelerometer(data):
  x, y, z, o = unpack_from('>hhhB', data[3:])
  print(f'x: {x}, y: {y}, z: {z}, o: {o}')

data = b'aB\x00\x0f0\x00\x00\x03\xe0\xff\xe0\x00\x10\x00K'
# parseAccelerometer(data)
print(prettify_bytearray(data))  # header

header, length, i, k, x, y, z, o = unpack_from('<HHBBhhhB', data)
print('header: ', header, '\t', prettify_bytearray(data[0:2]))
print('length: ', length, '\t', prettify_bytearray(data[2:4]))
print('i: ', i, '\t\t', prettify_bytearray(data[4:5]))
print('k: ', k, '\t\t', prettify_bytearray(data[5:6]))
print('x: ', x, '\t', prettify_bytearray(data[6:8]))
print('y: ', y, '\t', prettify_bytearray(data[8:10]))
print('z: ', z, '\t', prettify_bytearray(data[10:12]))
print('o: ', o, '\t\t', prettify_bytearray(data[12:13]))

# print(prettify_bytearray(data[0:2]))  # header
# print(prettify_bytearray(data[3:4]))  # hlength
# exit()

def createChecksum(bytearray):
    return (255 - (sum(bytearray) & 255)) & 255;

def createPacket(payload):
    start = b'\x41\x62'  # Ab from client, server responds with Ba
    packetSize = pack('>H', 5 + len(payload))
    packet = start + packetSize + payload
    packet += pack('B', createChecksum(packet))
    print(f"Sending packet: {packet}, (length: {len(packet)})")
    print(f"  {prettify_bytearray(packet)} (length: {len(packet)}")
    return packet

def validate_checksum(data):
    return (sum(data) & 255) == 255

def notification_handler(characteristic: BleakGATTCharacteristic, packet: bytearray):
    if len(packet) < 8:
        print(f"Error: response packet size should be >= 8 (was {len(packet)})")
        raise
    elif not validate_checksum(packet):
        print("Checksum validation failed")
        raise

    header, length, op1, op2 = unpack_from('<HHBB', packet)
    print('header: ', header, '\t', prettify_bytearray(packet[0:2]))
    print('length: ', length, '\t', prettify_bytearray(packet[2:4]))
    print('op1: ', op1, '\t\t', prettify_bytearray(packet[4:5]))
    print('op2: ', op2, '\t\t', prettify_bytearray(packet[5:6]))

    # data = packet[4:-1]  # the packet without header and checksum
    data = packet[6:-1]  # the packet without headers and checksum
    print(f'Response data: {data} (length: {len(data)}, checksum OK)')
    print(f'  {prettify_bytearray(data)}')

cmd_serial = b'\x00\x01\x02'
cmd_accelerometer = b'\x30\x00'

async def main():
    dev = None
    devices = await BleakScanner.discover()
    for d in devices:
        if d.name.startswith('INSTAX-')  and d.name.endswith('(IOS)'):
            dev = d
            break
    if not dev:
        print("No printer found")
        exit()

    print(f'Found instax printer {dev.name} at {dev.address}')

    async with BleakClient(dev.address) as client:
        print('connected')
        await client.start_notify(notifyUUID, notification_handler)

        packet = createPacket(cmd_serial) # Request serial number
        await client.write_gatt_char(writeUUID, packet)

        await asyncio.sleep(5.0)

asyncio.run(main())

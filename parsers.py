#!/usr/bin/env python3

from struct import unpack_from

def XYZ_AXIS_INFO(data):
    # if len(data) < 16:
    #     _logger.error(f"Response packet size should be >= 16 (was {len(data)})");
    #     return

    unknown, x, y, z, o = unpack_from('>BhhhB', data)
    print(f'x: {x}, y: {y}, z: {z}, o: {o}')

def DEVICE_INFO_SERVICE(data):
    serialNumber = data.decode('utf-8')
    print(f'Serialnumber: {serialNumber}')

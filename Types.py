#!/usr/bin/env python3

from enum import Enum

# Not sure yet where these fit in, but they are used in the original code
# 0 = VOLTAGE_INFO
# 1 = COLOR_INFO
# 2 = SW_INFO

# effects
# NONE(0),
# MONOCHROME(1),
# SEPIA(2),
# AUTO(3);

# The original code has a lot more color values, but I've only added the ones that
# are in use to this file
Imgproc_COLOR_RGB2YUV_YV12 = 131
Imgproc_COLOR_BGR2YUV_YV12 = 132

PrinterSettings = {
    'mini': {
        'modelName': 'Instax Mini Link',
        'chunkSize': 900,
        'exampleImage': 'example-mini.jpg',
        'width': 600,
        'height': 800
    },
    'square': {
        'modelName': 'Instax Square Link',
        'chunkSize': 1808,
        'exampleImage': 'example-square.jpg',
        'width': 800,
        'height': 800
    },
    'wide': {
        'modelName': 'Instax Wide Link',
        'chunkSize': 1808,
        'exampleImage': 'example-wide.jpg',
        'width': 1260,
        'height': 800
    },
    'dummy': {
        'modelName': 'Dummy Printer',
        'chunkSize': 123,
        'exampleImage': 'example-mini.jpg',
        'width': 10,
        'height': 20
    }
}


class EventType (Enum):
    """ Events we can send to the printer """
    UNKNOWN = (-1, -1)
    SUPPORT_FUNCTION_AND_VERSION_INFO = (0, 0)  # 0x00, 0x00
    DEVICE_INFO_SERVICE = (0, 1)  # 0x00, 0x01
    SUPPORT_FUNCTION_INFO = (0, 2)  # 0x00, 0x02
    IDENTIFY_INFORMATION = (0, 16)  # 0x00, 0x10
    SHUT_DOWN = (1, 0)  # 0x01, 0x00
    RESET = (1, 1)  # 0x01, 0x01
    AUTO_SLEEP_SETTINGS = (1, 2)  # 0x01, 0x02
    BLE_CONNECT = (1, 3)  # 0x01, 0x03
    PRINT_IMAGE_DOWNLOAD_START = (16, 0)  # 0x10, 0x00
    PRINT_IMAGE_DOWNLOAD_DATA = (16, 1)  # 0x10, 0x01
    PRINT_IMAGE_DOWNLOAD_END = (16, 2)  # 0x10, 0x02
    PRINT_IMAGE_DOWNLOAD_CANCEL = (16, 3)  # 0x10, 0x03
    PRINT_IMAGE = (16, 128)  # 0x10, 0x80
    REJECT_FILM_COVER = (16, 129)  # 0x10, 0x81
    FW_DOWNLOAD_START = (32, 0)  # 0x20, 0x00
    FW_DOWNLOAD_DATA = (32, 1)  # 0x20, 0x01
    FW_DOWNLOAD_END = (32, 2)  # 0x20, 0x02
    FW_UPGRADE_EXIT = (32, 3)  # 0x20, 0x03
    FW_PROGRAM_INFO = (32, 16)  # 0x20, 0x10
    FW_DATA_BACKUP = (32, 128)  # 0x20, 0x80
    FW_UPDATE_REQUEST = (32, 129)  # 0x20, 0x81
    XYZ_AXIS_INFO = (48, 0)  # 0x30, 0x00
    LED_PATTERN_SETTINGS = (48, 1)  # 0x30, 0x01
    AXIS_ACTION_SETTINGS = (48, 2)  # 0x30, 0x02
    LED_PATTERN_SETTINGS_DOUBLE = (48, 3)  # 0x30, 0x03
    POWER_ONOFF_LED_SETTING = (48, 4)  # 0x30, 0x04
    AR_LED_VIBRARTION_SETTING = (48, 6)  # 0x30, 0x06
    ADDITIONAL_PRINTER_INFO = (48, 16)  # 0x30, 0x10
    PRINTER_HEAD_LIGHT_CORRECT_INFO = (48, 128)  # 0x30, 0x80
    PRINTER_HEAD_LIGHT_CORRECT_SETTINGS = (48, 129)  # 0x30, 0x81
    CAMERA_SETTINGS = (128, 0)  # 0x80, 0x00
    CAMERA_SETTINGS_GET = (128, 1)  # 0x80, 0x01
    URL_UPLOAD_INFO = (129, 0)  # 0x81, 0x00
    URL_PICTURE_UPLOAD_START = (129, 1)  # 0x81, 0x01
    URL_PICTURE_UPLOAD = (129, 2)  # 0x81, 0x02
    URL_PICTURE_UPLOAD_END = (129, 3)  # 0x81, 0x03
    URL_AUDIO_UPLOAD_START = (129, 4)  # 0x81, 0x04
    URL_AUDIO_UPLOAD = (129, 5)  # 0x81, 0x05
    URL_AUDIO_UPLOAD_END = (129, 6)  # 0x81, 0x06
    URL_UPLOAD_ADDRESS = (129, 7)  # 0x81, 0x07
    URL_UPLOAD_DATA_COMPLETE = (129, 8)  # 0x81, 0x08
    LIVE_VIEW_START = (130, 0)  # 0x82, 0x00
    LIVE_VIEW_RECEIVE = (130, 1)  # 0x82, 0x01
    LIVE_VIEW_STOP = (130, 2)  # 0x82, 0x02
    LIVE_VIEW_TAKE_PICTURE = (130, 16)  # 0x82, 0x10
    POST_VIEW_UPLOAD_START = (130, 32)  # 0x82, 0x20
    POST_VIEW_UPLOAD = (130, 33)  # 0x82, 0x21
    POST_VIEW_UPLOAD_END = (130, 34)  # 0x82, 0x22
    POST_VIEW_PRINT = (130, 48)  # 0x82, 0x30
    FRAME_PICTURE_DOWNLOAD_START = (Imgproc_COLOR_RGB2YUV_YV12, 0)  # 0x83, 0x00
    FRAME_PICTURE_DOWNLOAD = (Imgproc_COLOR_RGB2YUV_YV12, 1)  # 0x83, 0x01
    FRAME_PICTURE_DOWNLOAD_END = (Imgproc_COLOR_RGB2YUV_YV12, 2)  # 0x83, 0x02
    FRAME_PICTURE_NAME_SETTING = (Imgproc_COLOR_RGB2YUV_YV12, 3)  # 0x83, 0x03
    FRAME_PICTURE_NAME_GET = (Imgproc_COLOR_RGB2YUV_YV12, 4)  # 0x83, 0x04
    CAMERA_LOG_SUBTOTAL_START = (Imgproc_COLOR_BGR2YUV_YV12, 0)  # 0x84, 0x00
    CAMERA_LOG_SUBTOTAL_DATA = (Imgproc_COLOR_BGR2YUV_YV12, 1)  # 0x84, 0x01
    CAMERA_LOG_SUBTOTAL_CLEAR = (Imgproc_COLOR_BGR2YUV_YV12, 2)  # 0x84, 0x02
    CAMERA_LOG_DATE_START = (Imgproc_COLOR_BGR2YUV_YV12, 3)  # 0x84, 0x03
    CAMERA_LOG_DATE_DATA = (Imgproc_COLOR_BGR2YUV_YV12, 4)  # 0x84, 0x04
    CAMERA_LOG_DATE_CLEAR = (Imgproc_COLOR_BGR2YUV_YV12, 5)  # 0x84, 0x05
    CAMERA_LOG_FILTER_START = (Imgproc_COLOR_BGR2YUV_YV12, 6)  # 0x84, 0x06
    CAMERA_LOG_FILTER_DATA = (Imgproc_COLOR_BGR2YUV_YV12, 7)  # 0x84, 0x07
    CAMERA_LOG_FILTER_CLEAR = (Imgproc_COLOR_BGR2YUV_YV12, 8)  # 0x84, 0x08


class InfoType (Enum):
    """ Payload types to use with EventType.DEVICE_INFO_SERVICE """
    IMAGE_SUPPORT_INFO = 0
    BATTERY_INFO = 1
    PRINTER_FUNCTION_INFO = 2
    PRINT_HISTORY_INFO = 3
    CAMERA_FUNCTION_INFO = 4
    CAMERA_HISTORY_INFO = 5

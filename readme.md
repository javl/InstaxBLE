# Instax-Bluetooth

<img align="right" style="margin:10px" src="https://github.com/javl/InstaxBLE/blob/main/instax-ble.gif?raw=true">

## Control your Instax Mini Link printer from Python

This Python module can be used to control your Instax bluetooth printer. Only tested with the Instax Mini Link, but it should also work with other bluetooth Instax models (though you might have to experiment with the image size when using the Square or Wide models).

This is a 100% certified Alpha state project: the code is working, but it's far from being finished or polished. Create an issue if you run into any trouble (but please read the rest of this readme first).

### Useful to know
These printers advertise themselves as two separate bluetooth periphials: `INSTAX-xxxxxxxx(IOS)` and `INSTAX-xxxxxxxx(ANDROID)` (where the x's are a unique number for your device).
When connected to the Android version data is send over a socket: this works well on Linux but I don't think this works on Windows or MacOS. Currently the code in the `main` branch of this repo uses this and so will only work on Linux based systems.

The IOS version of the Instax device uses `gatt` commands, which you can find in the (even more experimental) `gatt` branch in this repo. This works both on Linux and MacOS (not sure about Windows) but has a huge drawback on Linux. On connecting to the printer on MacOS the system and the printer will decice on a (high) transfer speed together, but on Linux you're stuck at the lowest transfer speed, meaning it can take up to a minute to send the image to the printer.

### Raspberry Pi
When scanning for bluetooth devices my Raspberry Pi 3 seems unable to find the `INSTAX-xxx(ANDROID)` device. However, I am able to connect to it if I enter the device address manually. 

The `INSTAX-xxx(ANDROID)` and `INSTAX-xxx(IOS)` endpoints share part of their address: if you can find the address for the IOS endpoint it looks something like `FA:AB:BC:xx:xx:xx`, while the Android one looks like `88:B4:36:xx:xx:xx`. So if you can find one, just swap out the first 6 characters to get the other one.

An alternative way to find it is via your Android phone: open the Instax app and connect to your printer,  then go to your phone's bluetooth settings and in the known devices list tap the gear next to the Instax device. It will show the device address (probably something like `88:B4:36:xx:xx:xx`) at the bottom of the screen. Make sure to disconnect / forget the device before connecting from another device.
You can now enter this address directy when creating your `InstaxBLE` instance instead of having the script search for it:

    instax = InstaxBLE(deviceAddress='88:B4:36:xx:xx:xx')
    


### Notes on usage

* The printer only works with .jpg images. I haven't actually tested this, but the printer code seems to suggest this.
* The script does not yet check if your image is the right size or orientation. I've tested printing with images that are 600x800 pixels and don't know what happens when you send your image in landscape orientation so you might want to rotate it beforehand.
* For faster (and possibly more reliable) printing remove any exifdata from your image. This will reduce the amount of data that needs to be send to the device.
* Your image should be 65535 bytes or less.

### Wifi
If you want to control one of the WiFi enabled Instax printers instead, you can use [Instax-api](https://github.com/jpwsutton/instax_api). This script borrows heavily from notes and ideas shared in [this instax-api thread](https://github.com/jpwsutton/instax_api/issues/21#issuecomment-1352639100).

### Installing and running

    git clone https://github.com/javl/InstaxBLE.git
    cd InstaxBle
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python3 InstaxBLE.py

### Enable printing
By default printing is disabled so you can test your code without the risk of accidental prints.
To enable printing, call `instax.enable_printing()` or specify `printingEnabled=True` in the constructor.

    instax = InstaxBle(enablePrinting=True)
    # or
    instax = InstaxBle()
    instax.enable_printing()

### Using a specific printer
By default InstaxBle connects to the first printer it can find. You can specify the name of the printer you want to connect to in the constructor. Note: you need to use the device name that ends in `(Android)`, not `(IOS)`:

    instax = InstaxBle(deviceName='Instax-12345678(Android)')

or specify the device address instead:

    instax = InstaxBLE(deviceAddress='88:B4:36:xx:xx:xx')



### Sending LED patterns
Controlling the LED on the printer works by sending patterns: series of colors to be displayed in order. You can find some patterns to use in `LedPatterns.py`, for example:

    import LedPatterns
    ...
    instax.send_led_pattern(LedPatterns.pulseGreen)

You can tweak these using a couple of extra settings:
1. `speed`: how long to show each color for (higher is a slower animation)
2. `repeat`:
    1. `0` plays the animation once
    2. `1`-`254` repeats the animation n-times
    3. `255` repeats forever
3. `when`: patterns can start playing at different moments. Allowed values are:
   1. `0` normal
   2. `1` on print
   3. `2` on print complete
   4. `3` pattern swap (not sure what this is)

So for example, to make the LED blink blue:

    send_led_pattern(colors=[[0, 0, 255], [0, 0, 0]], speed=5, repeat=255, when=0)
    # or while getting the color pattern from `LedPatterns`
    send_led_pattern(LedPatterns.blinkBLue, speed=5, repeat=255, when=0)


## Possible updates:
Printing process:
- [ ] Currently both the socket and gatt version of this script send the image over in chunks of 900 bytes, like the Android app does. But the IOS app actually sends the image in chunks of 1808 bytes. Currently the gatt version of the script is extremely slow on Linux, but if we increase this chunk size we might be able to reduce the waiting time by 50%. Worth a try.

Printer info:
- [ ] Get battery level
- [ ] Get number of photo's left in cartridge

Image enhancements:
- [ ] Auto rotate image to portrait before sending
- [ ] Convert to jpg if given a different filetype
- [ ] Strip exif data to decrease filesize
- [ ] Automatically lower the quality of the image to keep images below the 65535 bytes (0xFF 0xFF) file limit

#### image credit
Test pattern image from [Vecteezy](https://www.vecteezy.com/free-vector/test-pattern)

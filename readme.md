# Instax-BLE

![instax-ble-gif](https://user-images.githubusercontent.com/734644/208236529-550df42b-6d06-46ef-a38b-e683698d9ef6.gif)

### Control your Instax Mini Link printer from Python

This Python module can be used to control your Instax bluetooth printer. Only tested with the Instax Mini Link, but it should also work with other bluetooth Instax models (though you might have to experiment with the image size when using the Square or Wide models).

This code is working, but it's far from being finished or polished. Create an issue if you run into any trouble.

Some notes on the current state of this module:

* The script does not check if your image is the right size or orientation. I've tested printing with imags that are 600x800 pixels and don't know what happens when you send your image in landscape orientation so you might want to rotate it beforehand.
* For faster (and possibly more reliable) printing remove any exifdata from your image. This will reduce the amount of data that needs to be send to the device.

If you want to control one of the WiFi enabled printers instead, you can use [Instax-api](https://github.com/jpwsutton/instax_api). This script borrows heavily from notes and ideas as discussed in [this](https://github.com/jpwsutton/instax_api/issues/21#issuecomment-1352639100) instax-api thread.
### Enable printing
By default printing is disabled so you can test your code without the risk of accidental prints.
To enable printing, call `instax.enable_printing()` or specify `printingEnabled=True` in the constructor.

    instax = InstaxBle(enablePrinting=True)
    # or
    instax = InstaxBle()
    instax.enable_printing()

### Using a specific printer
By default InstaxBle connects to the first printer it can find. You can specify the name of the printer you want to connect to in the constructor. Note: you need to use the device name that ends in `(Android)`, not `(IOS)`:

`instax = InstaxBle(printerName='Instax-123456(Android)')`

### Sending LED patterns
Controlling the LED on the printer works by sending patterns: series of colors to be displayed in order. You can tweak these using a couple of extra settings:
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

Test pattern image from [Vecteezy](https://www.vecteezy.com/free-vector/test-pattern)

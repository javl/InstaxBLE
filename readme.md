# Instax-Bluetooth

<img align="right" style="margin:10px" src="https://github.com/javl/InstaxBLE/blob/main/instax-ble.gif?raw=true">

## Control your Instax Mini Link printer from Python

This module can be used to control your Instax bluetooth printer from Python. I've only been able to test with the Instax Mini Link, but it should also work with other bluetooth Instax models, though you might have to experiment when using the Square or Wide models.

Create an issue if you run into any trouble, but please read the rest of this readme first.

### Useful to know

#### 1. Printing is disabled by default
By default the `instax.print_image()` method will send all data to the printer _except_ the final print command. This is to prevent accidental prints when you're still testing your code. To allow printing either call `instax.enable_printing()` at any time after creating your `InstaxBLE` instance or enable it at creation time by specifying `print_enabled=True` in the constructor:

    instax = InstaxBLE()
    instax.connect()
    instax.enable_printing()  # allow printing
    instax.print_image('image.jpg')  # print image

or

    instax = InstaxBLE(print_enabled=True)  # enable printing at creation time
    instax.connect()
    instax.print_image('image.jpg')  # print image

#### 2. Connecting to a specific printer

By default, this script will connect to the first Instax printer it can find, but you can also specify the name (`device_name`) or address (`device_address`) of the printer you want to connect to:

    instax = InstaxBle()  # use the first printer you can find
    instax = InstaxBle(device_name='INSTAX-12345678')  # you can ommit the (Android) or (IOS) part you might see in your Bluetooth settings
    instax = InstaxBle(device_address='FA:AB:BC:xx:xx:xx')

#### 3. Gracefully disconnect on Exceptions

It's recommended to wrap your code inside a `try ... catch` loop so you can catch any errors (or `KeyboardInterrupt`) and disconnect from the printer gracefully before dropping out of your code. Otherwise your printer will think it's still connected and you'll have to manually restart it to reconnect.

        try:
            instax = InstaxBle()
            instax.connect()
            instax.enable_printing()
            instax.print_image('image.jpg')
        except Exception as e:
            print(e)
        finally:
            instax.disconnect()

### Notes on usage

1. The printer only works with .jpg images. I haven't actually tested this, but the printer code seems to suggest this.
2. The script does not yet check if your image is the right size or orientation. I've tested printing with images that are 600x800 pixels and don't know what happens when you send your image in landscape orientation so you might want to rotate it beforehand.
3. Your image should be 65535 bytes or less.
4. For faster (and possibly more reliable) printing remove any exifdata from your image. This will reduce the amount of data that needs to be send to the device. This also leaves more space for the image itself.

### Installing and running

    git clone https://github.com/javl/InstaxBLE.git
    cd InstaxBle
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python3 InstaxBLE.py

## Todo / Possible updates:

#### Testing:
- [x] Test on Linux
- [ ] Test on Raspberry Pi
- [ ] Test on MacOS
- [ ] Test on Windows

#### Printer info:
- [ ] Get battery level
- [ ] Get number of photo's left in cartridge
- [ ] Get accelerometer data

#### Image enhancements:
I'm not sure what happens when you send a different filetype or image in landscape orientation, but assuming those will fail:
- [ ] Resize if image too small or too large (needs to be 600x800 px)
- [ ] Resize if file size too large (max 65535 bytes)
- [ ] Auto rotate image to portrait before sending
- [ ] Convert to jpg if given a different filetype
- [ ] Strip exif data to decrease filesize
- [ ] Automatically lower the quality of the image to keep images below the 65535 bytes (0xFF 0xFF) file limit

### Instax WiFi printers
If you want to control one of the WiFi enabled Instax printers instead, you can use [Instax-api](https://github.com/jpwsutton/instax_api).

#### Credit
* Huge thank you to everyone in [this instax-api thread](https://github.com/jpwsutton/instax_api/issues/21#issuecomment-1352639100) (and @hermanneduard specifically) for their help in reverse engineering the Bluetooth protocol used.
* Thanks to @kdewald for his help and patience in getting [simplepyble](https://pypi.org/project/simplepyble/) to work.
* Test pattern image: [Test Pattern Vectors by Vecteezy](https://www.vecteezy.com/free-vector/test-pattern)

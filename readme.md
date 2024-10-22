# Instax-BLE

<img align="right" style="margin:10px" src="https://github.com/javl/Instax-Bluetooth/blob/main/instax-bluetooth.gif?raw=true">

## Control your Instax Link printer from Python

This module can be used to control your Instax bluetooth printer (**Mini**, **Square** and **Wide**) from Python. Create an issue if you run into any trouble, but please read the rest of this readme first.

Did you find this script useful? Feel free to support my open source software:

[![GitHub Sponsor](https://img.shields.io/github/sponsors/javl?label=Sponsor&logo=GitHub)](https://github.com/sponsors/javl)

[![BMC](https://www.buymeacoffee.com/assets/img/custom_images/white_img.png)](https://www.buymeacoffee.com/javl)


Don't need a whole Python script and just want to print? [This website](https://instax-link-web.vercel.app/) based on InstaxBLE lets you print to your Instax printer straight from your browser (repo [over here](https://github.com/linssenste/instax-link-web)).

### Supported printer models
This script has been tested with the Instax Mini Link, Instax Square Link and Instax Wide Link. I'm unsure about the other bluetooth models; if you have a different model please let met know if this code works for you. If needed you can find some info on recording the bluetooth data between your phone and the printer [here (Android)](https://github.com/javl/InstaxBLE/issues/4#issuecomment-1484123671) and [here (IOS)](https://github.com/jpwsutton/instax_api/issues/21#issuecomment-751651250). The IOS logs are strongly prefered as Android uses a slightly different way of communicating.

@ Fuijfilm: feel free to send me some of your other models if you want me to support those as well ;)

Do you have an older **WIFI** printer instead? Try [Instax-api](https://github.com/jpwsutton/instax_api).


| Model | Tested |
| --- | --- |
| Instax Mini Link | :heavy_check_mark: |
| Instax Mini Link 2 | :white_circle: |
| Instax Mini LiPlay | :heavy_check_mark: |
| Instax Square Link | :heavy_check_mark: |
| Instax Square Wide | :heavy_check_mark: |


### Image sizes accepted by the printers
The image send to the printer should be a JPEG at a specific image size, depending on the printer model. This script will automatically convert, resize and reduce quality to match the required specifications. This will work fine for most images, but if you want to prepare them manually you can use the info below:

| Model | Image size | File size |
| --- | --- | --- |
| Instax Mini Link | 600 x 800px | 105KB |
| Instax Mini Link 2 | 600 x 800px (a guess) | " |
| Instax Mini LiPlay | 600 x 800px (a guess) | " |
| Instax Square Link | 800 x 800px | " |
| Instax Square Wide | 1260 x 840px | " |

### Installing and running

    # Clone the repo
    git clone https://github.com/javl/InstaxBLE.git
    cd InstaxBLE

    # create a virtual environment and install the needed dependencies
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

    # Run the example
    python3 instax-ble.py


### Useful to know

#### 1. Printing is disabled by default
By default the `instax.print_image()` method will send all data to the printer _except_ for the final print command. This is to prevent accidental prints when you're still testing your code. To allow printing either call `instax.enable_printing()` at any time after creating your `InstaxBLE` instance or enable it at creation time by specifying `print_enabled=True` in the constructor:

    instax = InstaxBLE()
    instax.connect()
    instax.enable_printing()  # allow printing
    instax.print_image('image.jpg')  # print image
    instax.disconnect()  # all done, disconnect

or

    instax = InstaxBLE(print_enabled=True)  # enable printing at initialization
    instax.connect()
    instax.print_image('image.jpg')  # print image
    instax.disconnect()  # all done, disconnect

#### 2. Connecting to a specific printer

By default, this script will connect to the first Instax printer it can find, but you can also specify the name (`device_name`) or address (`device_address`) of the printer you want to connect to:

    # use the first printer that we can find (default):
    instax = InstaxBle()
    # Connect to a printer by device name. Ommit the (Android) or (IOS) part you might see in your Bluetooth settings:
    instax = InstaxBle(device_name='INSTAX-12345678')
    # Connect to a printer by device address (probably starts with FA:AB:BC):
    instax = InstaxBle(device_address='FA:AB:BC:xx:xx:xx')

#### 3. Gracefully disconnect on Exceptions

It's recommended to wrap your code inside a `try / except / finally` loop so you can catch any errors (or `KeyboardInterrupt`) and disconnect from the printer gracefully before dropping out of your code. Otherwise you might have to manually restart your printer for it to connect again. An orange light on the printer often means something went wrong: just turn if off and on again to reset.

        try:
            instax = InstaxBle()
            instax.connect()
            instax.enable_printing()
            instax.print_image('image.jpg')
        except Exception as e:
            print(e)
        finally:
            instax.disconnect()

### Using InstaxBLE in your own project
One of the simplest ways to use InstaxBLE in your own project is to put the InstaxBLE folder inside your own project folder and import it:

    from InstaxBLE.InstaxBLE import InstaxBLE
    instax = InstaxBLE()
    # the rest of your script
    # see the main() function in InstaxBLE.py for an example

## Todo / Possible updates:

#### Testing:
_Please let me know if you've managed to use this code on an unchecked platform_
- :heavy_check_mark: Test on Linux
- :heavy_check_mark: Test on MacOS
- :white_large_square: Test on Raspberry Pi
- :white_large_square: Test on Windows

#### Printer info:
Some of these options have already been explored in other branches, but I need to bring them into the main branch.
- :heavy_check_mark: Get battery level
- :heavy_check_mark: Get number of photo's left in cartridge
- :heavy_check_mark: Get accelerometer data
- :white_large_square: Get button press

#### Image enhancements:
I'm not sure what happens when you send a different filetype or image in landscape orientation, but assuming those will fail:
- :heavy_check_mark: Resize if image too small or too large (actual size depending on printer model)
- :heavy_check_mark: Resize if file size too large (max 65535 bytes)
- :white_large_square: Auto rotate image to portrait before sending
- :heavy_check_mark: Convert to jpg if given a different filetype
- :heavy_check_mark: Strip exif data to decrease filesize
- :heavy_check_mark: Automatically lower the quality of the image to keep images below the ~~65535 bytes (0xFF 0xFF)~~ 105KB file limit


#### Credit
* Huge thank you to everyone in [this instax-api thread](https://github.com/jpwsutton/instax_api/issues/21#issuecomment-1352639100) (and @hermanneduard specifically) for their help in reverse engineering the Bluetooth protocol used.
* Thanks to @kdewald for his help and patience in getting [simplepyble](https://pypi.org/project/simplepyble/) to work.
* Test pattern image: [Test Pattern Vectors by Vecteezy](https://www.vecteezy.com/free-vector/test-pattern)

#### License
This project is licensed under the [MIT License](LICENSE.md).

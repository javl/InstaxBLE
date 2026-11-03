#!/usr/bin/env python3
"""
Small Flask GUI for InstaxBLE.

Run it on a machine with working Bluetooth (on Windows, not WSL) and open
http://127.0.0.1:8765. Use --dummy to try the UI without a printer.
"""
import argparse
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from time import sleep

from flask import Flask, jsonify, request, send_file, send_from_directory
from PIL import Image, ImageColor, ImageOps

from InstaxBLE import InstaxBLE
from Types import PrinterSettings

MAX_UPLOAD_MB = 25
SEND_TIMEOUT_SECONDS = 120
DEFAULT_MODEL = PrinterSettings['mini']

app = Flask(__name__, static_folder=None)
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

# All Bluetooth work happens on a single worker thread so the (blocking)
# InstaxBLE calls never overlap and never block a request handler.
executor = ThreadPoolExecutor(max_workers=1)
lock = threading.Lock()
state = {'phase': 'disconnected', 'message': ''}
CONFIG_PATH = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'InstaxBLE' / 'config.json'
options = {'dummy': False, 'auto_connect': False}
RETRY_SECONDS = 10
instax = None


def load_saved():
    """ The remembered printer as {'address': ..., 'name': ...}, or None """
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        return data if data.get('address') else None
    except (OSError, ValueError):
        return None


def save_saved(device):
    if device is None:
        CONFIG_PATH.unlink(missing_ok=True)
        return
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(device), encoding='utf-8')


def set_state(phase, message=''):
    with lock:
        state['phase'] = phase
        state['message'] = message


def printer_size():
    """ (width, height) of the connected printer, or the Mini's size if unknown """
    settings = instax.printerSettings if instax and instax.printerSettings else DEFAULT_MODEL
    return settings['width'], settings['height']


def prepare_image(file_storage, fit, rotate, background):
    """ Fit the uploaded image to the printer's size and return it as a JPEG in a BytesIO """
    image = ImageOps.exif_transpose(Image.open(file_storage.stream))
    image = image.convert('RGB')
    if rotate:
        image = image.rotate(-rotate, expand=True)
    size = printer_size()
    if fit == 'pad':
        image = ImageOps.pad(image, size, Image.Resampling.LANCZOS, color=background)
    else:
        image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format='JPEG', quality=95)
    buffer.seek(0)
    return buffer


def image_from_request():
    file = request.files.get('image')
    if not file:
        raise ValueError('No image uploaded')
    fit = request.form.get('fit', 'crop')
    if fit not in ('crop', 'pad'):
        raise ValueError('Invalid fit mode')
    rotate = int(request.form.get('rotate', 0))
    if rotate not in (0, 90, 180, 270):
        raise ValueError('Invalid rotation')
    background = ImageColor.getrgb(request.form.get('background', '#ffffff'))
    return prepare_image(file, fit, rotate, background)


def link_is_up():
    """ Whether the Bluetooth link to the printer is still alive """
    if options['dummy']:
        return True
    try:
        return bool(instax and instax.peripheral and instax.peripheral.is_connected())
    except Exception:
        return False


def status_payload():
    # the printer can be switched off or go out of range at any time
    if state['phase'] == 'connected' and not link_is_up():
        set_state('disconnected', 'Lost connection to the printer.')
    with lock:
        payload = dict(state)
    payload['dummy'] = options['dummy']
    payload['saved'] = load_saved()
    payload['printer'] = None
    if instax and payload['phase'] in ('connected', 'printing') and instax.printerSettings:
        payload['printer'] = {
            'address': None if options['dummy'] else instax.peripheral.address(),
            'model': instax.printerSettings['modelName'],
            'photosLeft': instax.photosLeft,
            'battery': instax.batteryPercentage,
            'charging': instax.isCharging,
            'width': instax.printerSettings['width'],
            'height': instax.printerSettings['height'],
        }
    return payload


def do_connect():
    global instax
    set_state('connecting', 'Searching for printer...')
    try:
        saved = load_saved()
        instax = InstaxBLE(dummy_printer=options['dummy'], verbose=True,
                           device_address=saved['address'] if saved else None)
        instax.connect(timeout=30)
        if options['dummy']:
            instax.photosLeft, instax.batteryPercentage = 10, 100
        elif not instax.peripheral or not instax.peripheral.is_connected():
            set_state('disconnected', 'No printer found. Is it on and in range?')
            return
        elif not instax.printerSettings:
            set_state('disconnected', 'Connected, but the printer did not report its model.')
            instax.disconnect()
            return
        set_state('connected')
    except SystemExit as e:  # InstaxBLE exits when there is no Bluetooth adapter
        set_state('disconnected', str(e) or 'No Bluetooth adapter found.')
    except Exception as e:
        set_state('disconnected', f'{type(e).__name__}: {e}')


def do_disconnect():
    options['auto_connect_paused'] = True  # a manual disconnect should stick
    try:
        if instax:
            instax.disconnect()
    finally:
        set_state('disconnected')


def do_refresh():
    instax.get_printer_info()
    sleep(1)


def do_print(image, enabled):
    set_state('printing', 'Sending image...')
    try:
        if enabled:
            instax.enable_printing()
        instax.print_image(image)
        waited = 0
        while instax.packetsForPrinting and not options['dummy']:  # a dummy printer never drains the queue
            if waited >= SEND_TIMEOUT_SECONDS:
                instax.packetsForPrinting = []
                raise TimeoutError('printer stopped responding while sending')
            sleep(0.2)
            waited += 0.2
        sleep(2)
        set_state('connected', 'Sent to printer.' if enabled else 'Dry run finished (nothing was printed).')
    except Exception as e:
        set_state('connected', f'Print failed: {type(e).__name__}: {e}')
    finally:
        instax.disable_printing()


@app.get('/')
def index():
    return send_from_directory('web', 'index.html')


@app.get('/api/status')
def api_status():
    return jsonify(status_payload())


@app.post('/api/connect')
def api_connect():
    if state['phase'] != 'disconnected':
        return jsonify(error='Already connected or connecting'), 409
    options['auto_connect_paused'] = False
    set_state('connecting', 'Searching for printer...')
    executor.submit(do_connect)
    return jsonify(status_payload()), 202


@app.post('/api/disconnect')
def api_disconnect():
    if state['phase'] in ('disconnected', 'printing'):
        return jsonify(error='Not connected, or a print is in progress'), 409
    executor.submit(do_disconnect)
    return jsonify(status_payload()), 202


@app.post('/api/refresh')
def api_refresh():
    if state['phase'] != 'connected':
        return jsonify(error='Not connected'), 409
    executor.submit(do_refresh)
    return jsonify(status_payload()), 202


@app.post('/api/preview')
def api_preview():
    try:
        image = image_from_request()
    except Exception as e:
        return jsonify(error=str(e)), 400
    return send_file(image, mimetype='image/jpeg')


@app.post('/api/print')
def api_print():
    if state['phase'] != 'connected':
        return jsonify(error='Not connected'), 409
    if instax.photosLeft == 0:
        return jsonify(error='The printer has no film left'), 409
    try:
        image = image_from_request()
    except Exception as e:
        return jsonify(error=str(e)), 400
    dry_run = request.form.get('dry_run', 'true') != 'false'
    set_state('printing', 'Sending image...')
    executor.submit(do_print, image, not dry_run)
    return jsonify(status_payload()), 202


@app.post('/api/remember')
def api_remember():
    """ Remember the connected printer so we only ever auto-connect to it """
    if state['phase'] != 'connected' or options['dummy'] or not instax or not instax.peripheral:
        return jsonify(error='Connect to a real printer first'), 409
    save_saved({'address': instax.peripheral.address(), 'name': instax.peripheral.identifier()})
    return jsonify(status_payload())


@app.post('/api/forget')
def api_forget():
    save_saved(None)
    return jsonify(status_payload())


def auto_connect_loop():
    """ Keep trying to connect whenever we're disconnected (e.g. printer switched on later) """
    while True:
        sleep(RETRY_SECONDS)
        if options.get('auto_connect_paused') or not (load_saved() or options['dummy']):
            continue  # only auto-connect to a remembered printer, never to whichever one is nearby
        status_payload()  # notices a lost link and flips the phase to disconnected
        with lock:
            if state['phase'] != 'disconnected':
                continue
            state['phase'], state['message'] = 'connecting', 'Searching for printer...'
        executor.submit(do_connect)


def configure(dummy=False, auto_connect=True):
    """ Set up dummy mode and auto-connect (used by main() and by the tray launcher) """
    options['dummy'] = dummy
    if auto_connect:
        options['auto_connect'] = True
        threading.Thread(target=auto_connect_loop, daemon=True).start()
    if dummy:
        # InstaxBLE looks for a Bluetooth adapter even in dummy mode
        import simplepyble
        simplepyble.Adapter.get_adapters = staticmethod(lambda: [object()])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1', help='use 0.0.0.0 to allow other devices on your network')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--dummy', action='store_true', help='fake printer, for trying the UI without Bluetooth')
    parser.add_argument('--no-auto-connect', action='store_true', help="don't connect to the printer automatically")
    args = parser.parse_args()

    configure(dummy=args.dummy, auto_connect=not args.no_auto_connect)
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == '__main__':
    main()

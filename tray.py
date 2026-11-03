#!/usr/bin/env python3
"""
System tray launcher for the InstaxBLE web GUI (Windows).

Runs the Flask server in the background with a tray icon to open the page,
toggle start-at-login, or quit. Start it with pythonw.exe so no console window
appears. Logs go to %LOCALAPPDATA%\\InstaxBLE\\instax.log.
"""
import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path

from PIL import Image, ImageDraw
from werkzeug.serving import make_server

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
RUN_VALUE = 'InstaxBLE'


def log_dir():
    path = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'InstaxBLE'
    path.mkdir(parents=True, exist_ok=True)
    return path


def redirect_output_to_log():
    """ pythonw has no stdout/stderr, so send them to a log file """
    if sys.stdout is None or sys.stderr is None:
        stream = open(log_dir() / 'instax.log', 'a', buffering=1, encoding='utf-8')
        sys.stdout = sys.stdout or stream
        sys.stderr = sys.stderr or stream


def autostart_command(port, dummy):
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    command = f'"{pythonw if pythonw.exists() else sys.executable}" "{Path(__file__).resolve()}" --no-browser --port {port}'
    return command + (' --dummy' if dummy else '')


def autostart_enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, RUN_VALUE)
            return True
    except FileNotFoundError:
        return False


def set_autostart(enabled, port=8765, dummy=False):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, autostart_command(port, dummy))
        else:
            try:
                winreg.DeleteValue(key, RUN_VALUE)
            except FileNotFoundError:
                pass


def make_icon():
    """ A simple camera-ish glyph so we don't have to ship an image file """
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((4, 14, 60, 56), radius=8, fill=(212, 56, 44, 255))
    draw.rectangle((20, 8, 44, 16), fill=(212, 56, 44, 255))
    draw.ellipse((20, 22, 44, 46), fill=(255, 255, 255, 255))
    draw.ellipse((26, 28, 38, 40), fill=(40, 40, 40, 255))
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--dummy', action='store_true', help='fake printer, for trying things out')
    parser.add_argument('--no-auto-connect', action='store_true', help="don't connect to the printer automatically")
    parser.add_argument('--no-browser', action='store_true', help="don't open the page on launch (used for start at login)")
    parser.add_argument('--set-autostart', choices=('on', 'off'), help='enable or disable start at login, then exit')
    args = parser.parse_args()

    if args.set_autostart:
        set_autostart(args.set_autostart == 'on', args.port, args.dummy)
        return

    redirect_output_to_log()
    url = f'http://127.0.0.1:{args.port}'

    import app as webapp
    webapp.configure(dummy=args.dummy, auto_connect=not args.no_auto_connect)
    try:
        server = make_server('127.0.0.1', args.port, webapp.app, threaded=True)
    except OSError:
        # already running (or the port is taken): just show the page
        webbrowser.open(url)
        return
    threading.Thread(target=server.serve_forever, daemon=True).start()

    import pystray

    def open_page(icon=None, item=None):
        webbrowser.open(url)

    def toggle_autostart(icon, item):
        set_autostart(not autostart_enabled(), args.port, args.dummy)

    def quit_app(icon, item):
        server.shutdown()
        icon.stop()

    icon = pystray.Icon(
        'InstaxBLE', make_icon(), 'Instax Printer',
        menu=pystray.Menu(
            pystray.MenuItem('Open', open_page, default=True),
            pystray.MenuItem('Start at login', toggle_autostart, checked=lambda item: autostart_enabled()),
            pystray.MenuItem('Quit', quit_app),
        ),
    )
    if not args.no_browser:
        open_page()
    icon.run()


if __name__ == '__main__':
    main()

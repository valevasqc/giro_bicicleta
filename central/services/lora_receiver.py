"""Central-side LoRa receiver that runs in a background thread."""

import threading
import time
import serial
from central import config


class LoRaReceiver:
    """Receive station messages and forward raw lines to a callback."""

    def __init__(self, stub: bool, port: str, baud: int, on_message):
        """Create serial receiver, or no-op receiver in stub mode."""
        self.stub = stub
        self.on_message = on_message  # callback(raw_line: str)
        self._stop = threading.Event()
        if not stub:
            self._ser = serial.Serial(port, baud, timeout=0.5)
            time.sleep(2)
            self._ser.reset_input_buffer()
        else:
            self._ser = None

    def start(self):
        """Start the background read loop."""
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def send(self, message: str) -> bool:
        """Send one LoRa line to a station."""
        if self.stub:
            print(f'[LoRa STUB TX central] {message}')
            return True
        try:
            self._ser.write((message.strip() + '\n').encode())
            return True
        except Exception as e:
            print(f'[LoRa central] TX error: {e}')
            return False

    def _loop(self):
        """Continuously read serial lines until stopped."""
        if self.stub:
            return
        while not self._stop.is_set():
            try:
                line = self._ser.readline().decode('utf-8', errors='ignore').strip()
                if line and not line.startswith('TX result:') and not line.startswith('READY'):
                    self.on_message(line)
            except Exception as e:
                print(f'[LoRa receiver] error: {e}')
                time.sleep(1)

    def stop(self):
        """Signal the receiver loop to stop."""
        self._stop.set()

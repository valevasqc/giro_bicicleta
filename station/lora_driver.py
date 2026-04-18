"""Station-side serial LoRa driver with optional stub mode."""

import threading
import serial
import serial.tools.list_ports
from station import config


class LoRaDriver:
    """Thin wrapper around pyserial for station TX/RX."""

    def __init__(self, stub: bool, port: str, baud: int):
        """Initialize serial connection, or skip hardware in stub mode."""
        self.stub = stub
        self._lock = threading.Lock()
        if not stub:
            self._ser = serial.Serial(port, baud, timeout=0.1)
            # Wait for READY from ESP32
            import time
            time.sleep(2)
            self._ser.reset_input_buffer()
        else:
            self._ser = None

    def send(self, message: str) -> bool:
        """Send one LoRa line. Returns True on success."""
        if self.stub:
            print(f'[LoRa STUB TX] {message}')
            return True
        try:
            with self._lock:
                self._ser.write((message.strip() + '\n').encode())
            return True
        except Exception as e:
            print(f'[LoRa] TX error: {e}')
            return False

    def readline(self) -> str | None:
        """Read one filtered line from LoRa, or None when no usable packet."""
        if self.stub:
            return None
        try:
            line = self._ser.readline().decode('utf-8', errors='ignore').strip()
            # Filter out ESP32 debug lines
            if line and not line.startswith('TX result:') and not line.startswith('ERROR') and not line.startswith('READY'):
                return line
            return None
        except Exception:
            return None

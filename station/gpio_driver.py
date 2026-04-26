import logging
import threading
import time

logger = logging.getLogger(__name__)


class GPIODriver:
    """Controls the physical lock and reads dock/charge reed switches.

    In stub mode (no Raspberry Pi hardware) every mutating call prints its
    action and sensor reads return their default stub values, so the full
    rental flow can be exercised on a laptop without any GPIO library.

    Args:
        stub:       When True, print-only mode; no RPi.GPIO calls are made.
        lock_pin:   BCM GPIO pin number connected to the lock solenoid (OUT).
        dock_pin:   BCM GPIO pin number connected to the dock reed switch (IN).
        charge_pin: BCM GPIO pin number connected to the charge reed switch (IN).
    """

    def __init__(
        self,
        stub_lock: bool,
        stub_sensors: bool,
        lock_pin,
        dock_pin,
        charge_pin,
        lock_unlocks_when_high: bool = True,
        stub_dock_occupied: bool = True,
        stub_charge_connected: bool = True,
    ):
        self._stub_lock = stub_lock
        self._stub_sensors = stub_sensors
        self._lock_pin = lock_pin
        self._dock_pin = dock_pin
        self._charge_pin = charge_pin
        self._lock_unlocks_when_high = bool(lock_unlocks_when_high)
        self._stub_dock_occupied = bool(stub_dock_occupied)
        self._stub_charge_connected = bool(stub_charge_connected)

        if not stub_lock or not stub_sensors:
            import RPi.GPIO as GPIO  # noqa: PLC0415
            self._GPIO = GPIO
            GPIO.setmode(GPIO.BCM)
            if lock_pin is not None and not stub_lock:
                GPIO.setup(lock_pin, GPIO.OUT, initial=self._locked_level())
            if dock_pin is not None and not stub_sensors:
                GPIO.setup(dock_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            if charge_pin is not None and not stub_sensors:
                GPIO.setup(charge_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def _unlock_level(self):
        return self._GPIO.HIGH if self._lock_unlocks_when_high else self._GPIO.LOW

    def _locked_level(self):
        return self._GPIO.LOW if self._lock_unlocks_when_high else self._GPIO.HIGH

    def unlock_for_seconds(self, duration: float) -> bool:
        """Briefly open the electromagnetic lock then re-engage it.

        Returns True if the unlock command was issued successfully, False otherwise.
        In stub mode always returns True.
        """
        if self._stub_lock:
            logger.debug("[GPIO STUB] unlock_for_seconds(%ss) on LOCK_PIN=%s", duration, self._lock_pin)
            return True

        if self._lock_pin is None:
            return False

        try:
            self._GPIO.output(self._lock_pin, self._unlock_level())

            def _relock():
                time.sleep(duration)
                self._GPIO.output(self._lock_pin, self._locked_level())

            threading.Thread(target=_relock, daemon=True).start()
            return True
        except Exception as exc:
            logger.warning("[GPIO] unlock_for_seconds failed: %s", exc)
            return False

    def read_dock_occupied(self) -> bool:
        """Return True if a bike is present in the dock (reed switch closed).

        In stub mode returns configured stub_dock_occupied default.
        """
        if self._stub_sensors:
            logger.debug("[GPIO STUB] read_dock_occupied() on DOCK_PIN=%s -> %s", self._dock_pin, self._stub_dock_occupied)
            return self._stub_dock_occupied

        if self._dock_pin is None:
            return False

        try:
            return not bool(self._GPIO.input(self._dock_pin))  # active-low
        except Exception as exc:
            logger.warning("[GPIO] read_dock_occupied failed: %s", exc)
            return False

    def read_charge_connected(self) -> bool:
        """Return True if the charging cable is plugged in (reed switch closed).

        In stub mode returns configured stub_charge_connected default.
        """
        if self._stub_sensors:
            logger.debug("[GPIO STUB] read_charge_connected() on CHARGE_PIN=%s -> %s", self._charge_pin, self._stub_charge_connected)
            return self._stub_charge_connected

        if self._charge_pin is None:
            return False

        try:
            return not bool(self._GPIO.input(self._charge_pin))  # active-low
        except Exception as exc:
            logger.warning("[GPIO] read_charge_connected failed: %s", exc)
            return False

    def read_lock_confirmed(self) -> bool:
        """Return True when the bike-return reed switch indicates a secured return.

        Current hardware maps lock confirmation to the return/dock reed switch.
        """
        return self.read_dock_occupied()

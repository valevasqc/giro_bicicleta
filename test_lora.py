import argparse
import time
import sys

from serial import SerialException

from central.services.lora_receiver import LoRaReceiver


def on_msg(raw):
    print(f'GOT: {raw}')


def normalize_port(port: str) -> str:
    if port.startswith('/dev/'):
        return port
    if port.startswith('cu.'):
        return f'/dev/{port}'
    return port


def main() -> None:
    parser = argparse.ArgumentParser(description='LoRa serial smoke test.')
    parser.add_argument('--port', default='/dev/cu.usbmodem101', help='Serial port path.')
    parser.add_argument('--baud', type=int, default=115200, help='Serial baud rate.')
    args = parser.parse_args()

    port = normalize_port(args.port)
    try:
        r = LoRaReceiver(stub=False, port=port, baud=args.baud, on_message=on_msg)
    except SerialException as exc:
        if 'Resource busy' in str(exc):
            print(f'Port is busy: {port}')
            print('Close Arduino Serial Monitor (or any app using the port), then retry.')
            print(f'Tip: lsof {port}')
            sys.exit(1)
        raise
    r.start()

    time.sleep(2)
    r.send('RENTAL_APPROVED|S1|B1|U1|2024-01-01T00:00:00Z')  # station board should print this

    print(f'Listening on {port} @ {args.baud}. Type messages in station Serial Monitor')
    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()

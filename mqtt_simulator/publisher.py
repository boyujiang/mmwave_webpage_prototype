"""Standalone publisher for the project's MQTT vitals contract."""

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

try:
    from .vitals import SCENARIOS, VitalsSimulator
except ImportError:
    from vitals import SCENARIOS, VitalsSimulator


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Publish simulated vitals to esp/room/<room>/vitals."
        )
    )
    parser.add_argument(
        "--room",
        action="append",
        dest="rooms",
        default=None,
        help="Room to simulate; repeat as needed (default: 101).",
    )
    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="normal",
    )
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Publishing cycles; 0 runs until Ctrl+C.",
    )
    parser.add_argument("--seed", type=int)
    parser.add_argument(
        "--host",
        default=os.getenv("MQTT_BROKER_HOST", "127.0.0.1"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MQTT_BROKER_PORT", "1883")),
    )
    parser.add_argument("--keepalive", type=int, default=60)
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"))
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"))
    parser.add_argument("--qos", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--retain", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print messages without connecting to a broker.",
    )
    return parser


def validate_options(parser, options):
    if options.interval < 0:
        parser.error("--interval must be zero or greater")
    if options.count < 0:
        parser.error("--count must be zero or greater")

    rooms = list(dict.fromkeys(options.rooms or ["101"]))
    if any(not room or "/" in room for room in rooms):
        parser.error("room numbers must be non-empty and cannot contain '/'")
    return rooms


def connect(options):
    connected = threading.Event()
    failure = []
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if options.username:
        client.username_pw_set(options.username, options.password)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            failure.append(str(reason_code))
        connected.set()

    client.on_connect = on_connect
    try:
        client.connect(options.host, options.port, options.keepalive)
        client.loop_start()
    except OSError as exc:
        raise RuntimeError(
            f"Cannot connect to MQTT broker "
            f"{options.host}:{options.port}: {exc}"
        ) from exc

    if not connected.wait(timeout=10):
        client.loop_stop()
        client.disconnect()
        raise RuntimeError("Timed out waiting for the MQTT broker")
    if failure:
        client.loop_stop()
        client.disconnect()
        raise RuntimeError(f"MQTT connection failed: {failure[0]}")
    return client


def run(options, rooms, output=print):
    simulator = VitalsSimulator(options.seed)
    client = None if options.dry_run else connect(options)
    cycles = 0

    try:
        while options.count == 0 or cycles < options.count:
            timestamp = datetime.now(timezone.utc)
            for room in rooms:
                payload = simulator.payload(
                    room,
                    options.scenario,
                    timestamp,
                )
                topic = f"esp/room/{room}/vitals"
                encoded = json.dumps(payload, separators=(",", ":"))

                if client is not None:
                    result = client.publish(
                        topic,
                        encoded,
                        qos=options.qos,
                        retain=options.retain,
                    )
                    if result.rc != mqtt.MQTT_ERR_SUCCESS:
                        raise RuntimeError(
                            f"Publish to {topic} failed: {result.rc}"
                        )
                    result.wait_for_publish(timeout=10)
                output(f"{topic} {encoded}")

            cycles += 1
            should_continue = options.count == 0 or cycles < options.count
            if should_continue and options.interval:
                time.sleep(options.interval)
    finally:
        if client is not None:
            client.loop_stop()
            client.disconnect()


def main(argv=None):
    parser = build_parser()
    options = parser.parse_args(argv)
    rooms = validate_options(parser, options)
    action = "Printing" if options.dry_run else "Publishing"
    print(
        f"{action} {options.scenario} vitals for "
        f"{', '.join(rooms)} every {options.interval:g}s"
    )
    try:
        run(options, rooms)
    except KeyboardInterrupt:
        print("Stopping MQTT simulator")
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""End-to-end MQTT contract probe using a temporary subscriber."""

import argparse
import json
import os
import threading
import time

import paho.mqtt.client as mqtt

try:
    from .publisher import build_parser as build_publisher_parser
    from .publisher import run as run_publisher
    from .publisher import validate_options
except ImportError:
    from publisher import build_parser as build_publisher_parser
    from publisher import run as run_publisher
    from publisher import validate_options


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Publish test vitals and verify that the MQTT broker delivers "
            "the expected messages."
        )
    )
    parser.add_argument("--room", action="append", dest="rooms")
    parser.add_argument("--scenario", default="normal")
    parser.add_argument(
        "--host",
        default=os.getenv("MQTT_BROKER_HOST", "127.0.0.1"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MQTT_BROKER_PORT", "1883")),
    )
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"))
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"))
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def valid_payload(payload):
    required = {
        "heart_rate",
        "respiration",
        "activity_status",
        "in_bed",
        "in_room",
        "timestamp",
    }
    return (
        isinstance(payload, dict)
        and required == set(payload)
        and isinstance(payload["heart_rate"], (int, float))
        and 0 <= payload["heart_rate"] <= 300
        and isinstance(payload["respiration"], (int, float))
        and 0 <= payload["respiration"] <= 100
        and payload["activity_status"]
        in {"standing", "sitting", "walking", "lying_down"}
        and isinstance(payload["in_bed"], bool)
        and isinstance(payload["in_room"], bool)
        and isinstance(payload["timestamp"], str)
    )


def publisher_options(options, rooms):
    parser = build_publisher_parser()
    arguments = [
        "--count",
        "1",
        "--interval",
        "0",
        "--scenario",
        options.scenario,
        "--host",
        options.host,
        "--port",
        str(options.port),
        "--seed",
        str(options.seed),
    ]
    for room in rooms:
        arguments.extend(("--room", room))
    if options.username:
        arguments.extend(("--username", options.username))
    if options.password:
        arguments.extend(("--password", options.password))
    publisher = parser.parse_args(arguments)
    validate_options(parser, publisher)
    return publisher


def main(argv=None):
    options = build_parser().parse_args(argv)
    rooms = list(dict.fromkeys(options.rooms or ["101"]))
    expected_topics = {f"esp/room/{room}/vitals" for room in rooms}
    received = {}
    subscribed = threading.Event()
    complete = threading.Event()
    failure = []
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if options.username:
        client.username_pw_set(options.username, options.password)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            failure.append(f"Subscriber connection failed: {reason_code}")
            complete.set()
            return
        client.subscribe("esp/room/+/vitals")

    def on_subscribe(client, userdata, mid, reason_codes, properties):
        subscribed.set()

    def on_message(client, userdata, message):
        if message.topic not in expected_topics:
            return
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            failure.append(f"{message.topic}: invalid JSON: {exc}")
            complete.set()
            return
        if not valid_payload(payload):
            failure.append(f"{message.topic}: payload contract failed")
            complete.set()
            return
        received[message.topic] = payload
        if expected_topics <= set(received):
            complete.set()

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message

    try:
        client.connect(options.host, options.port, 60)
        client.loop_start()
        if not subscribed.wait(options.timeout):
            raise RuntimeError("Subscriber did not connect and subscribe")

        run_publisher(publisher_options(options, rooms), rooms, output=lambda _: None)
        complete.wait(options.timeout)
    except (OSError, RuntimeError) as exc:
        failure.append(str(exc))
    finally:
        client.loop_stop()
        client.disconnect()

    if failure:
        for error in failure:
            print(f"FAIL: {error}")
        return 1

    missing = expected_topics - set(received)
    if missing:
        print("FAIL: timed out waiting for " + ", ".join(sorted(missing)))
        return 1

    for topic in sorted(received):
        print(f"PASS: {topic} delivered a contract-valid payload")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

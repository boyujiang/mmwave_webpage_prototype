import json
import logging
import re

import paho.mqtt.client as mqtt
from django.conf import settings
from django.core.management.base import BaseCommand

from analytics.mqtt_bridge import MQTTBridge


logger = logging.getLogger(__name__)
TOPIC_PATTERN = re.compile(r"^esp/room/(?P<room_number>[^/]+)/vitals$")


class Command(BaseCommand):
    help = "Subscribe to room vitals over MQTT and forward them to Django."

    def handle(self, *args, **options):
        bridge = MQTTBridge()
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        if settings.MQTT_USERNAME:
            client.username_pw_set(
                settings.MQTT_USERNAME,
                settings.MQTT_PASSWORD,
            )

        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code != 0:
                self.stderr.write(
                    self.style.ERROR(
                        f"MQTT connection failed: {reason_code}"
                    )
                )
                return

            client.subscribe(settings.MQTT_TOPIC)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Subscribed to {settings.MQTT_TOPIC}"
                )
            )

        def on_message(client, userdata, message):
            match = TOPIC_PATTERN.fullmatch(message.topic)
            if match is None:
                logger.warning("Ignoring unexpected topic %s", message.topic)
                return

            try:
                payload = json.loads(message.payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                logger.warning(
                    "Invalid JSON payload on %s",
                    message.topic,
                )
                return

            if not isinstance(payload, dict):
                logger.warning(
                    "MQTT payload on %s must be an object",
                    message.topic,
                )
                return

            bridge.handle_vitals(
                match.group("room_number"),
                payload,
            )

        client.on_connect = on_connect
        client.on_message = on_message

        self.stdout.write(
            f"Connecting to MQTT broker "
            f"{settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}"
        )
        client.connect(
            settings.MQTT_BROKER_HOST,
            settings.MQTT_BROKER_PORT,
            settings.MQTT_KEEPALIVE,
        )

        try:
            client.loop_forever()
        except KeyboardInterrupt:
            self.stdout.write("Stopping MQTT subscriber")
        finally:
            client.disconnect()

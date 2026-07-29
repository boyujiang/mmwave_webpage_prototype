# analytics/mqtt_bridge.py

import logging

from .models import Resident, ResidentVitals
from .realtime import publish_resident_vitals
from .serializers import VitalsPayloadSerializer

logger = logging.getLogger(__name__)


class MQTTBridge:
    """验证并处理已经完成 MQTT topic 路由的生命体征消息。"""

    def handle_vitals(self, room_number: str, payload: dict) -> None:
        serializer = VitalsPayloadSerializer(data=payload)

        if not serializer.is_valid():
            logger.warning(
                "Invalid vitals payload for room %s: %s",
                room_number,
                serializer.errors,
            )
            return

        data = serializer.validated_data

        try:
            resident = Resident.objects.get(
                room_number=room_number,
            )
        except Resident.DoesNotExist:
            logger.warning(
                "No resident configured for room %s",
                room_number,
            )
            return

        try:
            vitals = ResidentVitals.objects.create(
                resident=resident,
                heart_rate=data["heart_rate"],
                respiration=data["respiration"],
                activity_status=data["activity_status"],
                in_bed=data["in_bed"],
                in_room=data["in_room"],
                recorded_at=data["timestamp"],
            )
        except Exception:
            logger.exception(
                "Failed to save vitals for room %s",
                room_number,
            )
            return

        publish_resident_vitals(resident, vitals)

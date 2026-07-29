from decimal import Decimal

from asgiref.sync import async_to_sync
from django.core.cache import cache
from django.utils import timezone


def resident_status(vitals):
    if (
        not vitals.in_bed
        and vitals.activity_status == "lying_down"
    ):
        return "fall_detected"

    hour = timezone.now().hour
    is_overnight = hour >= 22 or hour <= 6
    if not vitals.in_bed and not vitals.in_room and is_overnight:
        return "room_departure"

    return "stable"


def build_vitals_message(resident, vitals):
    respiration = vitals.respiration
    if isinstance(respiration, Decimal):
        respiration = float(respiration)

    return {
        "resident_id": resident.pk,
        "room_number": str(resident.room_number),
        "heart_rate": vitals.heart_rate,
        "respiration": respiration,
        "activity_status": vitals.activity_status,
        "in_bed": vitals.in_bed,
        "in_room": vitals.in_room,
        "recorded_at": vitals.recorded_at.isoformat(),
        "status": resident_status(vitals),
        "alert_dismissed_at": (
            resident.alert_dismissed_at.isoformat()
            if resident.alert_dismissed_at
            else None
        ),
    }


def publish_resident_vitals(resident, vitals):
    # Import lazily so task and test discovery do not initialize Channels.
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if channel_layer is None:
        raise RuntimeError("Django channel layer is not configured")

    payload = build_vitals_message(resident, vitals)
    cache.set(
        f"vitals:resident:{resident.pk}",
        payload,
        timeout=300,
    )

    event = {
        "type": "vitals_update",
        "data": payload,
    }
    for group_name in (
        f"vitals.resident.{resident.pk}",
        "vitals.all",
    ):
        async_to_sync(channel_layer.group_send)(
            group_name,
            event,
        )

    return payload

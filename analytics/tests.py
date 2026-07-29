from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import RefreshToken

from analytics.models import Resident, ResidentVitals
from analytics.mqtt_bridge import MQTTBridge
from myproject.asgi import application


TEST_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}


@override_settings(
    ALLOWED_HOSTS=["localhost", "testserver"],
    CHANNEL_LAYERS=TEST_CHANNEL_LAYERS,
    CACHES=TEST_CACHES,
)
class VitalsWebSocketTests(TransactionTestCase):
    def test_authenticated_client_receives_vitals_update(self):
        user = get_user_model().objects.create_user(
            username="caregiver",
            email="caregiver@example.com",
            password="test-password",
        )
        token = str(RefreshToken.for_user(user).access_token)

        async_to_sync(self._assert_vitals_delivery)(token)

    def test_mqtt_bridge_persists_and_pushes_snapshot(self):
        user = get_user_model().objects.create_user(
            username="snapshot-caregiver",
            email="snapshot@example.com",
            password="test-password",
        )
        resident = Resident.objects.create(
            name="Test Resident",
            room_number="101",
        )
        token = str(RefreshToken.for_user(user).access_token)

        MQTTBridge().handle_vitals("101", {
            "heart_rate": 72,
            "respiration": 16,
            "activity_status": "sitting",
            "in_bed": True,
            "in_room": True,
            "timestamp": "2026-07-22T12:00:00Z",
        })

        self.assertEqual(ResidentVitals.objects.count(), 1)
        async_to_sync(self._assert_snapshot_delivery)(
            token,
            resident.pk,
        )

    async def _assert_vitals_delivery(self, token):
        communicator = WebsocketCommunicator(
            application,
            "/ws/analytics/vitals/",
            headers=[(b"origin", b"http://localhost:3000")],
            subprotocols=["access-token", token],
        )

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, f"WebSocket closed with {subprotocol}")
        self.assertEqual(subprotocol, "access-token")

        payload = {
            "resident_id": 1,
            "room_number": "101",
            "heart_rate": 72,
            "respiration": 16,
            "activity_status": "sitting",
            "in_bed": True,
            "in_room": True,
            "recorded_at": "2026-07-22T12:00:00+00:00",
            "status": "stable",
            "alert_dismissed_at": None,
        }
        await get_channel_layer().group_send(
            "vitals.all",
            {
                "type": "vitals_update",
                "data": payload,
            },
        )

        message = await communicator.receive_json_from(timeout=1)
        self.assertEqual(message["type"], "vitals_update")
        self.assertEqual(message["data"], payload)
        await communicator.disconnect()

    async def _assert_snapshot_delivery(self, token, resident_id):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/analytics/residents/{resident_id}/vitals/",
            headers=[(b"origin", b"http://localhost:3000")],
            subprotocols=["access-token", token],
        )

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected, f"WebSocket closed with {subprotocol}")

        message = await communicator.receive_json_from(timeout=1)
        self.assertEqual(message["type"], "vitals_snapshot")
        self.assertEqual(message["data"]["resident_id"], resident_id)
        self.assertEqual(message["data"]["heart_rate"], 72)
        self.assertIsNone(message["data"]["alert_dismissed_at"])
        await communicator.disconnect()

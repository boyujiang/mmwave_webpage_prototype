from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache


class VitalsConsumer(AsyncJsonWebsocketConsumer):
    """Push MQTT-derived vitals events to authenticated WebSocket clients."""

    async def connect(self):
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close(code=4401)
            return

        raw_resident_id = self.scope["url_route"]["kwargs"].get(
            "resident_id"
        )

        try:
            self.resident_id = (
                int(raw_resident_id)
                if raw_resident_id is not None
                else None
            )
        except (TypeError, ValueError):
            await self.close(code=4400)
            return

        # A production multi-tenant deployment should also verify that this
        # user is allowed to see the requested resident.
        self.group_name = (
            f"vitals.resident.{self.resident_id}"
            if self.resident_id is not None
            else "vitals.all"
        )

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        subprotocol = (
            "access-token"
            if self.scope.get("jwt_subprotocol")
            else None
        )
        await self.accept(subprotocol=subprotocol)

        # REST supplies the list/dashboard bootstrap. A resident-specific
        # connection also gets the latest cached snapshot immediately.
        if self.resident_id is not None:
            latest = await sync_to_async(cache.get)(
                f"vitals:resident:{self.resident_id}"
            )
            if latest is not None:
                await self.send_json({
                    "type": "vitals_snapshot",
                    "data": latest,
                })

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

    async def vitals_update(self, event):
        data = event.get("data")

        if not isinstance(data, dict):
            return

        await self.send_json({
            "type": "vitals_update",
            "data": data,
        })

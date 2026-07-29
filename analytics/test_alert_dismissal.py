from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from analytics.models import Resident, ResidentVitals
from analytics.realtime import build_vitals_message
from analytics.tasks import check_alert_after_dismiss


class DismissAlertTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="dismiss-caregiver",
            email="dismiss@example.com",
            password="test-password",
        )
        self.resident = Resident.objects.create(
            name="Dismiss Test Resident",
            room_number="201",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("analytics.views.check_alert_after_dismiss.apply_async")
    def test_dismiss_schedules_check_five_minutes_later(self, apply_async):
        response = self.client.post(
            f"/api/analytics/residents/{self.resident.pk}/dismiss/",
        )

        self.assertEqual(response.status_code, 200)
        self.resident.refresh_from_db()
        self.assertIsNotNone(self.resident.alert_dismissed_at)
        apply_async.assert_called_once_with(
            args=[
                self.resident.pk,
                self.resident.alert_dismissed_at.isoformat(),
            ],
            countdown=300,
        )

    def test_stale_check_does_not_clear_a_newer_dismissal(self):
        old_dismissed_at = timezone.now()
        newer_dismissed_at = old_dismissed_at + timedelta(minutes=1)
        self.resident.alert_dismissed_at = newer_dismissed_at
        self.resident.save(update_fields=["alert_dismissed_at"])

        result = check_alert_after_dismiss.run(
            self.resident.pk,
            old_dismissed_at.isoformat(),
        )

        self.resident.refresh_from_db()
        self.assertEqual(
            self.resident.alert_dismissed_at,
            newer_dismissed_at,
        )
        self.assertIn("Ignored stale alert check", result)

    def test_realtime_payload_includes_dismissal_state(self):
        dismissed_at = timezone.now()
        self.resident.alert_dismissed_at = dismissed_at
        vitals = ResidentVitals.objects.create(
            resident=self.resident,
            heart_rate=72,
            respiration=16,
            activity_status="sitting",
            in_bed=True,
            in_room=True,
            recorded_at=timezone.now(),
        )

        payload = build_vitals_message(self.resident, vitals)

        self.assertEqual(
            payload["alert_dismissed_at"],
            dismissed_at.isoformat(),
        )

    @patch("analytics.realtime.publish_resident_vitals")
    def test_scheduled_check_clears_matching_dismissal(self, publish_vitals):
        dismissed_at = timezone.now()
        self.resident.alert_dismissed_at = dismissed_at
        self.resident.save(update_fields=["alert_dismissed_at"])
        vitals = ResidentVitals.objects.create(
            resident=self.resident,
            heart_rate=72,
            respiration=16,
            activity_status="lying_down",
            in_bed=False,
            in_room=True,
            recorded_at=timezone.now(),
        )

        result = check_alert_after_dismiss.run(
            self.resident.pk,
            dismissed_at.isoformat(),
        )

        self.resident.refresh_from_db()
        self.assertIsNone(self.resident.alert_dismissed_at)
        self.assertIn("alert will be shown", result)
        publish_vitals.assert_called_once()
        published_resident, published_vitals = publish_vitals.call_args.args
        self.assertEqual(published_resident.pk, self.resident.pk)
        self.assertEqual(published_vitals.pk, vitals.pk)

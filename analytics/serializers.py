from rest_framework import serializers
from .models import Resident, ResidentVitals, ResidentEvent


class ResidentVitalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResidentVitals
        fields = ['heart_rate', 'respiration', 'activity_level', 'recorded_at']


class ResidentEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)

    class Meta:
        model = ResidentEvent
        fields = ['id', 'event_type', 'event_type_display', 'timestamp', 'metadata']


class ResidentSerializer(serializers.ModelSerializer):
    latest_vitals = serializers.SerializerMethodField()
    today_bathroom_runs = serializers.SerializerMethodField()
    latest_events = serializers.SerializerMethodField()

    class Meta:
        model = Resident
        fields = [
            'id', 'name', 'room_number', 'date_of_birth',
            'latest_vitals', 'today_bathroom_runs', 'latest_events'
        ]

    def get_latest_vitals(self, obj):
        latest = obj.vitals.first()
        if latest:
            return ResidentVitalsSerializer(latest).data
        return None

    def get_today_bathroom_runs(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        today = timezone.now().date()
        return obj.events.filter(
            event_type='bathroom_run',
            timestamp__date=today
        ).count()

    def get_latest_events(self, obj):
        latest = obj.events.all()[:5]
        return ResidentEventSerializer(latest, many=True).data


class ResidentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resident
        fields = ['id', 'name', 'room_number', 'is_active']

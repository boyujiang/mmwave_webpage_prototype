from rest_framework import serializers
from .models import Resident, ResidentVitals, ResidentEvent, AlertNote


class ResidentVitalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResidentVitals
        fields = ['heart_rate', 'respiration', 'activity_status', 'in_bed', 'in_room', 'recorded_at']


class ResidentEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)

    class Meta:
        model = ResidentEvent
        fields = ['id', 'event_type', 'event_type_display', 'timestamp', 'metadata']


class ResidentSerializer(serializers.ModelSerializer):
    latest_vitals = serializers.SerializerMethodField()
    today_bathroom_runs = serializers.SerializerMethodField()
    latest_events = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Resident
        fields = [
            'id', 'name', 'room_number', 'date_of_birth', 'is_active', 'alert_dismissed_at',
            'latest_vitals', 'today_bathroom_runs', 'latest_events', 'status'
        ]

    def get_latest_vitals(self, obj):
        latest = obj.vitals.first()
        if latest:
            return ResidentVitalsSerializer(latest).data
        return None

    def get_status(self, obj):
        """Calculate resident status: stable, fall_detected, or room_departure"""
        from django.utils import timezone
        
        latest = obj.vitals.first()
        if not latest:
            return 'stable'
        
        hour = timezone.now().hour
        is_overnight = 22 <= hour or hour <= 6
        
        # Fall: not in bed + lying down
        if not latest.in_bed and latest.activity_status == 'lying_down':
            return 'fall_detected'
        
        # Room departure: not in bed + not in room + overnight
        if not latest.in_bed and not latest.in_room and is_overnight:
            return 'room_departure'
        
        return 'stable'

    def get_today_bathroom_runs(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        today = now.date()
        
        # Get events from 10pm today to 8am tomorrow
        start_time = timezone.make_aware(
            timezone.datetime(today.year, today.month, today.day, 22, 0, 0)
        )
        end_time = timezone.make_aware(
            timezone.datetime(today.year, today.month, today.day, 23, 59, 59)
        )
        
        # If it's before 8am today, also count from yesterday 10pm
        if now.hour < 8:
            yesterday = today - timedelta(days=1)
            start_time = timezone.make_aware(
                timezone.datetime(yesterday.year, yesterday.month, yesterday.day, 22, 0, 0)
            )
        
        return obj.events.filter(
            event_type='bathroom_run',
            timestamp__gte=start_time,
            timestamp__lte=end_time
        ).count()

    def get_latest_events(self, obj):
        latest = obj.events.all()[:5]
        return ResidentEventSerializer(latest, many=True).data


class ResidentListSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = Resident
        fields = ['id', 'name', 'room_number', 'is_active', 'status']

    def get_status(self, obj):
        from django.utils import timezone
        
        latest = obj.vitals.first()
        if not latest:
            return 'stable'
        
        hour = timezone.now().hour
        is_overnight = 22 <= hour or hour <= 6
        
        if not latest.in_bed and latest.activity_status == 'lying_down':
            return 'fall_detected'
        
        if not latest.in_bed and not latest.in_room and is_overnight:
            return 'room_departure'
        
        return 'stable'


class AlertNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertNote
        fields = ['id', 'alert_type', 'note', 'caregiver_name', 'created_at', 'is_dismissed', 'dismissed_at']

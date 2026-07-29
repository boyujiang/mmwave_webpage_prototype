# analytics/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from .models import DashboardConfig, Resident
from .serializers import ResidentSerializer
from .tasks import check_alert_after_dismiss
from .vitals_history import DEFAULT_METRIC, METRICS


class ConfigView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user configuration (rarely changes)"""
        config, _ = DashboardConfig.objects.get_or_create(
            user=request.user
        )
        return Response({
            'theme': config.theme,
            'refresh_interval': config.refresh_interval,
            'widgets': config.widgets,
        })
    
    def post(self, request):
        """Update configuration"""
        config, _ = DashboardConfig.objects.get_or_create(
            user=request.user
        )
        config.theme = request.data.get('theme', config.theme)
        config.refresh_interval = request.data.get('refresh_interval', config.refresh_interval)
        config.widgets = request.data.get('widgets', config.widgets)
        config.save()
        
        return Response({'status': 'updated'})


class ResidentListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all residents with their latest vitals and events"""
        residents = Resident.objects.filter(is_active=True)
        serializer = ResidentSerializer(residents, many=True)
        return Response(serializer.data)


class ResidentDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, resident_id):
        """Get specific resident details"""
        try:
            resident = Resident.objects.get(id=resident_id, is_active=True)
            serializer = ResidentSerializer(resident)
            return Response(serializer.data)
        except Resident.DoesNotExist:
            return Response({'error': 'Resident not found'}, status=404)


class ResidentVitalsHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, resident_id):
        """Get historical vitals data for charting"""
        metric = request.query_params.get('metric', 'hr')
        range_param = request.query_params.get('range', 'day')
        
        now = timezone.now()
        
        if range_param == 'hour':
            start_time = now - timedelta(hours=24)
        elif range_param == 'day':
            start_time = now - timedelta(days=7)
        else:
            start_time = now - timedelta(weeks=4)
        
        try:
            resident = Resident.objects.get(id=resident_id, is_active=True)
        except Resident.DoesNotExist:
            return Response({'error': 'Resident not found'}, status=404)
        
        metric_handler = METRICS.get(metric, DEFAULT_METRIC)
        if range_param == 'hour' and not metric_handler.supports_hourly:
            return Response({
                'data_avgs': [],
                'baseline': 0,
                'average': 0,
                'message': 'This metric only supports daily and weekly view'
            })

        return Response(
            metric_handler.get_history(resident, start_time, range_param)
        )


class AlertNoteView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, resident_id):
        """Get all alert notes for a resident - from files"""
        import os
        import json
        from pathlib import Path
        
        try:
            resident = Resident.objects.get(id=resident_id, is_active=True)
        except Resident.DoesNotExist:
            return Response({'error': 'Resident not found'}, status=404)
        
        # Notes stored in: analytics/notes/<resident_id>/
        notes_dir = Path(__file__).parent / 'notes' / str(resident_id)
        
        notes = []
        if notes_dir.exists():
            for note_file in sorted(notes_dir.glob('*.json'), reverse=True):
                try:
                    with open(note_file, 'r') as f:
                        note_data = json.load(f)
                        notes.append(note_data)
                except:
                    pass
        
        return Response(notes)
    
    def post(self, request, resident_id):
        """Create a new alert note - save to file"""
        import os
        import json
        from pathlib import Path
        
        try:
            resident = Resident.objects.get(id=resident_id, is_active=True)
        except Resident.DoesNotExist:
            return Response({'error': 'Resident not found'}, status=404)
        
        note = request.data.get('note', '')
        alert_type = request.data.get('alert_type', 'general')
        caregiver_name = request.user.get_full_name() or request.user.username
        
        if not note:
            return Response({'error': 'Note cannot be empty'}, status=400)
        
        # Create notes directory
        notes_dir = Path(__file__).parent / 'notes' / str(resident_id)
        notes_dir.mkdir(parents=True, exist_ok=True)
        
        # Create note file with timestamp as filename
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        note_file = notes_dir / f'{timestamp}.json'
        
        note_data = {
            'id': timestamp,
            'alert_type': alert_type,
            'note': note,
            'caregiver_name': caregiver_name,
            'created_at': timezone.now().isoformat(),
            'is_dismissed': False,
            'dismissed_at': None
        }
        
        with open(note_file, 'w') as f:
            json.dump(note_data, f)
        
        return Response(note_data, status=201)


class DismissAlertView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, resident_id):
        """Dismiss the current alert for a resident - set dismiss timestamp, check after 5 minutes"""
        from django.utils import timezone
        
        try:
            resident = Resident.objects.get(id=resident_id, is_active=True)
        except Resident.DoesNotExist:
            return Response({'error': 'Resident not found'}, status=404)
        
        # Record the dismiss time
        dismissed_at = timezone.now()
        resident.alert_dismissed_at = dismissed_at
        resident.save(update_fields=['alert_dismissed_at'])
        
        # Pass the dismissal timestamp so an older queued task cannot clear a
        # newer dismissal for the same resident.
        check_alert_after_dismiss.apply_async(
            args=[resident_id, dismissed_at.isoformat()],
            countdown=300,
        )
        
        return Response({'status': 'alert_dismissed', 'message': 'Alert dismissed. Will check again in 5 minutes.'})


class ToggleResidentActiveView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, resident_id):
        """Toggle resident's active status"""
        try:
            resident = Resident.objects.get(id=resident_id)
        except Resident.DoesNotExist:
            return Response({'error': 'Resident not found'}, status=404)
        
        resident.is_active = not resident.is_active
        resident.save()
        
        return Response({'is_active': resident.is_active})

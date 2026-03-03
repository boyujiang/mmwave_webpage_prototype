# analytics/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count
from django.utils import timezone
from datetime import timedelta
from .models import DashboardConfig, Resident, ResidentVitals, ResidentEvent, AlertNote
from .serializers import ResidentSerializer, AlertNoteSerializer


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
        
        # Metrics that don't support hourly (only daily/weekly)
        no_hourly_metrics = ['br', 'f', 'rd', 'w', 'ibt']
        if range_param == 'hour' and metric in no_hourly_metrics:
            return Response({
                'data_avgs': [],
                'baseline': 0,
                'average': 0,
                'message': 'This metric only supports daily and weekly view'
            })
        
        if metric == 'hr':
            vitals = ResidentVitals.objects.filter(
                resident=resident,
                recorded_at__gte=start_time
            ).order_by('recorded_at')
            
            # Aggregate by hour/day/week
            if range_param == 'hour':
                # Group by hour
                from django.db.models.functions import TruncHour
                grouped = vitals.annotate(period=TruncHour('recorded_at')).values('period').annotate(avg_val=Avg('heart_rate')).order_by('period')
                data = [{'timestamp': g['period'].isoformat(), 'value': round(g['avg_val'], 1)} for g in grouped if g['avg_val']]
            elif range_param == 'day':
                from django.db.models.functions import TruncDate
                grouped = vitals.annotate(period=TruncDate('recorded_at')).values('period').annotate(avg_val=Avg('heart_rate')).order_by('period')
                data = [{'timestamp': g['period'].isoformat(), 'value': round(g['avg_val'], 1)} for g in grouped if g['avg_val']]
            else:  # week
                from django.db.models.functions import TruncWeek
                grouped = vitals.annotate(period=TruncWeek('recorded_at')).values('period').annotate(avg_val=Avg('heart_rate')).order_by('period')
                data = [{'timestamp': g['period'].isoformat(), 'value': round(g['avg_val'], 1)} for g in grouped if g['avg_val']]
            
            baseline = 72
            avg_value = sum(d['value'] for d in data) / max(len(data), 1) if data else baseline
            
            return Response({
                'data_avgs': data,
                'baseline': baseline,
                'average': round(avg_value, 1)
            })
            
        elif metric == 'rr':
            vitals = ResidentVitals.objects.filter(
                resident=resident,
                recorded_at__gte=start_time
            ).order_by('recorded_at')
            
            # Aggregate by hour/day/week
            if range_param == 'hour':
                from django.db.models.functions import TruncHour
                grouped = vitals.annotate(period=TruncHour('recorded_at')).values('period').annotate(avg_val=Avg('respiration')).order_by('period')
                data = [{'timestamp': g['period'].isoformat(), 'value': round(g['avg_val'], 1)} for g in grouped if g['avg_val']]
            elif range_param == 'day':
                from django.db.models.functions import TruncDate
                grouped = vitals.annotate(period=TruncDate('recorded_at')).values('period').annotate(avg_val=Avg('respiration')).order_by('period')
                data = [{'timestamp': g['period'].isoformat(), 'value': round(g['avg_val'], 1)} for g in grouped if g['avg_val']]
            else:
                from django.db.models.functions import TruncWeek
                grouped = vitals.annotate(period=TruncWeek('recorded_at')).values('period').annotate(avg_val=Avg('respiration')).order_by('period')
                data = [{'timestamp': g['period'].isoformat(), 'value': round(g['avg_val'], 1)} for g in grouped if g['avg_val']]
            
            baseline = 16
            avg_value = sum(d['value'] for d in data) / max(len(data), 1) if data else baseline
            
            return Response({
                'data_avgs': data,
                'baseline': baseline,
                'average': round(avg_value, 1)
            })
            
        elif metric == 'activity':
            vitals = ResidentVitals.objects.filter(
                resident=resident,
                recorded_at__gte=start_time
            ).order_by('recorded_at')
            
            activity_map = {'lying_down': 1, 'sitting': 2, 'standing': 3, 'walking': 4}
            
            if range_param == 'hour':
                from django.db.models.functions import TruncHour
                grouped = vitals.annotate(period=TruncHour('recorded_at')).values('period')
                data = []
                for g in grouped:
                    # Get the most common activity in this hour
                    hour_vitals = ResidentVitals.objects.filter(
                        resident=resident,
                        recorded_at__hour=g['period'].hour,
                        recorded_at__date=g['period'].date()
                    )
                    activities = [activity_map.get(v.activity_status, 1) for v in hour_vitals]
                    if activities:
                        data.append({'timestamp': g['period'].isoformat(), 'value': round(sum(activities) / len(activities), 1)})
            elif range_param == 'day':
                from django.db.models.functions import TruncDate
                grouped = vitals.annotate(period=TruncDate('recorded_at')).values('period')
                data = []
                for g in grouped:
                    day_vitals = ResidentVitals.objects.filter(
                        resident=resident,
                        recorded_at__date=g['period']
                    )
                    activities = [activity_map.get(v.activity_status, 1) for v in day_vitals]
                    if activities:
                        data.append({'timestamp': g['period'].isoformat(), 'value': round(sum(activities) / len(activities), 1)})
            else:
                from django.db.models.functions import TruncWeek
                grouped = vitals.annotate(period=TruncWeek('recorded_at')).values('period')
                data = []
                for g in grouped:
                    week_vitals = ResidentVitals.objects.filter(
                        resident=resident,
                        recorded_at__gte=g['period'],
                        recorded_at__lt=g['period'] + timedelta(days=7)
                    )
                    activities = [activity_map.get(v.activity_status, 1) for v in week_vitals]
                    if activities:
                        data.append({'timestamp': g['period'].isoformat(), 'value': round(sum(activities) / len(activities), 1)})
            
            return Response({
                'data_avgs': data,
                'baseline': 1,
                'average': len(data) > 0 and sum(d['value'] for d in data) / len(data) or 1
            })
            
        elif metric == 'br':
            # Only daily and weekly
            events = ResidentEvent.objects.filter(
                resident=resident,
                event_type='bathroom_run',
                timestamp__gte=start_time
            ).order_by('timestamp')
            
            if range_param == 'day':
                from django.db.models.functions import TruncDate
                grouped = events.annotate(period=TruncDate('timestamp')).values('period').annotate(count=Count('id')).order_by('period')
                data = [{'timestamp': g['period'].isoformat(), 'value': g['count']} for g in grouped]
            else:  # week
                from django.db.models.functions import TruncWeek
                grouped = events.annotate(period=TruncWeek('timestamp')).values('period').annotate(count=Count('id')).order_by('period')
                data = [{'timestamp': g['period'].isoformat(), 'value': g['count']} for g in grouped]
            
            return Response({
                'data_avgs': data,
                'baseline': 0,
                'average': sum(d['value'] for d in data) / max(len(data), 1)
            })
            
        elif metric == 'f':
            events = ResidentEvent.objects.filter(
                resident=resident,
                event_type='fall_detected',
                timestamp__gte=start_time
            ).order_by('timestamp')
            
            if range_param == 'day':
                from django.db.models.functions import TruncDate
                grouped = events.annotate(period=TruncDate('timestamp')).values('period').annotate(count=Count('id')).order_by('period')
                data = [{'timestamp': g['period'].isoformat(), 'value': g['count']} for g in grouped]
            else:
                from django.db.models.functions import TruncWeek
                grouped = events.annotate(period=TruncWeek('timestamp')).values('period').annotate(count=Count('id')).order_by('period')
                data = [{'timestamp': g['period'].isoformat(), 'value': g['count']} for g in grouped]
            
            return Response({
                'data_avgs': data,
                'baseline': 0,
                'average': sum(d['value'] for d in data) / max(len(data), 1)
            })
            
        else:
            return Response({
                'data_avgs': [],
                'baseline': 0,
                'average': 0
            })


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
        resident.alert_dismissed_at = timezone.now()
        resident.save()
        
        # Schedule check after 5 minutes
        from analytics.tasks import check_alert_after_dismiss
        check_alert_after_dismiss.delay(resident_id)
        
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

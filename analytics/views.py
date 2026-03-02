# analytics/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg
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
            start_time = now - timedelta(hours=1)
        elif range_param == 'day':
            start_time = now - timedelta(days=1)
        else:
            start_time = now - timedelta(weeks=1)
        
        try:
            resident = Resident.objects.get(id=resident_id, is_active=True)
        except Resident.DoesNotExist:
            return Response({'error': 'Resident not found'}, status=404)
        
        if metric == 'hr':
            vitals = ResidentVitals.objects.filter(
                resident=resident,
                recorded_at__gte=start_time
            ).order_by('recorded_at')
            
            data = []
            for v in vitals:
                data.append({'timestamp': v.recorded_at.isoformat(), 'value': v.heart_rate})
            
            baseline = 72
            avg_value = vitals.aggregate(avg=Avg('heart_rate'))['avg'] or baseline
            
            return Response({
                'data_avgs': [{'timestamp': d['timestamp'], 'value': d['value']} for d in data],
                'baseline': baseline,
                'average': avg_value
            })
            
        elif metric == 'rr':
            vitals = ResidentVitals.objects.filter(
                resident=resident,
                recorded_at__gte=start_time
            ).order_by('recorded_at')
            
            data = []
            for v in vitals:
                data.append({'timestamp': v.recorded_at.isoformat(), 'value': v.respiration})
            
            baseline = 16
            avg_value = vitals.aggregate(avg=Avg('respiration'))['avg'] or baseline
            
            return Response({
                'data_avgs': [{'timestamp': d['timestamp'], 'value': d['value']} for d in data],
                'baseline': baseline,
                'average': avg_value
            })
            
        elif metric == 'activity':
            vitals = ResidentVitals.objects.filter(
                resident=resident,
                recorded_at__gte=start_time
            ).order_by('recorded_at')
            
            activity_map = {'lying_down': 1, 'sitting': 2, 'standing': 3, 'walking': 4}
            data = []
            for v in vitals:
                data.append({'timestamp': v.recorded_at.isoformat(), 'value': activity_map.get(v.activity_status, 1)})
            
            return Response({
                'data_avgs': data,
                'baseline': 1,
                'average': len(data) > 0 and sum(activity_map.get(v.activity_status, 1) for v in vitals) / len(vitals) or 1
            })
            
        elif metric == 'br':
            events = ResidentEvent.objects.filter(
                resident=resident,
                event_type='bathroom_run',
                timestamp__gte=start_time
            ).order_by('timestamp')
            
            data = []
            for e in events:
                data.append({'timestamp': e.timestamp.isoformat(), 'value': 1})
            
            return Response({
                'data_avgs': data,
                'baseline': 0,
                'average': len(data)
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
        """Dismiss the current alert for a resident - update file"""
        import json
        from pathlib import Path
        
        try:
            resident = Resident.objects.get(id=resident_id, is_active=True)
        except Resident.DoesNotExist:
            return Response({'error': 'Resident not found'}, status=404)
        
        notes_dir = Path(__file__).parent / 'notes' / str(resident_id)
        
        if not notes_dir.exists():
            return Response({'error': 'No notes found'}, status=404)
        
        # Find first undismissed note
        for note_file in sorted(notes_dir.glob('*.json')):
            try:
                with open(note_file, 'r') as f:
                    note_data = json.load(f)
                
                if not note_data.get('is_dismissed', False):
                    note_data['is_dismissed'] = True
                    note_data['dismissed_at'] = timezone.now().isoformat()
                    with open(note_file, 'w') as f:
                        json.dump(note_data, f)
                    return Response(note_data)
            except:
                pass
        
        return Response({'error': 'No active alert to dismiss'}, status=404)

# analytics/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg
from django.utils import timezone
from datetime import timedelta
from .models import DashboardConfig, Resident, ResidentVitals, ResidentEvent
from .serializers import ResidentSerializer


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

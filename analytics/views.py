# analytics/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import DashboardConfig, Resident
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

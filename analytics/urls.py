from django.urls import path
from .views import ConfigView, ResidentListView, ResidentDetailView

urlpatterns = [
    path('config/', ConfigView.as_view(), name='config'),
    path('residents/', ResidentListView.as_view(), name='residents'),
    path('residents/<int:resident_id>/', ResidentDetailView.as_view(), name='resident_detail'),
]

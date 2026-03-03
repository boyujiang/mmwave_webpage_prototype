from django.urls import path
from .views import ConfigView, ResidentListView, ResidentDetailView, ResidentVitalsHistoryView, AlertNoteView, DismissAlertView, ToggleResidentActiveView

urlpatterns = [
    path('config/', ConfigView.as_view(), name='config'),
    path('residents/', ResidentListView.as_view(), name='residents'),
    path('residents/<int:resident_id>/', ResidentDetailView.as_view(), name='resident_detail'),
    path('residents/<int:resident_id>/history/', ResidentVitalsHistoryView.as_view(), name='resident_history'),
    path('residents/<int:resident_id>/notes/', AlertNoteView.as_view(), name='resident_notes'),
    path('residents/<int:resident_id>/dismiss/', DismissAlertView.as_view(), name='dismiss_alert'),
    path('residents/<int:resident_id>/toggle-active/', ToggleResidentActiveView.as_view(), name='toggle_active'),
]

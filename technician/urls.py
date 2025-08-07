# technician/urls.py (updated)
from django.urls import path
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.conf.urls.static import static
from django.template.response import TemplateResponse
from portal.views import (LoginView, LogoutView, InterventionListView, InterventionDetailView,
                         InterventionUpdateStatusView, SecurityChecklistView,
                         PhotoUploadView, PhotosAfterView, VoiceRecordingView, CommentView, QualityControlView,
                         SignatureView, GetInterventionFilesView)
import json

def test_view(request):
    return HttpResponse("Django is working!")

def manifest_view(request):
    """Return the PWA manifest"""
    manifest = {
        "name": "Astro Tech Technician",
        "short_name": "AstroTech",
        "description": "Application mobile pour les techniciens Astro Tech",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#14224A",
        "orientation": "portrait",
        "scope": "/",
        "lang": "fr",
        "categories": ["productivity", "business"],
        "icons": [
            {
                "src": "/static/images/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/static/images/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ],
        "shortcuts": [
            {
                "name": "Interventions",
                "short_name": "Interventions",
                "description": "Voir toutes les interventions",
                "url": "/interventions/",
                "icons": [{"src": "/static/images/icon-96x96.png", "sizes": "96x96"}]
            }
        ]
    }

    return JsonResponse(manifest, content_type='application/manifest+json')

def service_worker_view(request):
    """Return the service worker file"""
    with open('portal/static/js/service-worker.js', 'r') as f:
        content = f.read()

    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response

def offline_view(request):
    """Offline fallback page"""
    return TemplateResponse(request, 'portal/offline.html')

urlpatterns = [
    path('test/', test_view, name='test'),
    path('', InterventionListView.as_view(), name='home'),

    # Auth
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # PWA routes
    path('manifest.json', manifest_view, name='manifest'),
    path('service-worker.js', service_worker_view, name='service_worker'),
    path('offline.html', offline_view, name='offline'),

    # Interventions
    path('interventions/', InterventionListView.as_view(), name='interventions'),
    path('interventions/<str:intervention_id>/update_status/',
         InterventionUpdateStatusView.as_view(),
         name='intervention_update_status'),
    path('interventions/<str:intervention_id>/', InterventionDetailView.as_view(), name='intervention_detail'),

    # Intervention steps
    path('interventions/<str:intervention_id>/security-checklist/',
         SecurityChecklistView.as_view(),
         name='security_checklist'),
    path('interventions/<str:intervention_id>/photo-upload/',
         PhotoUploadView.as_view(),
         name='photo_upload'),
    path('interventions/<str:intervention_id>/photos-after/',
         PhotosAfterView.as_view(),
         name='photos_after'),
    path('interventions/<str:intervention_id>/voice-recording/',
         VoiceRecordingView.as_view(),
         name='voice_recording'),
    path('interventions/<str:intervention_id>/comment/',
         CommentView.as_view(),
         name='comment'),
    path('interventions/<str:intervention_id>/quality-control/',
         QualityControlView.as_view(),
         name='quality_control'),
    path('interventions/<str:intervention_id>/signature/',
         SignatureView.as_view(),
         name='signature'),
    path('interventions/<str:intervention_id>/files/',
         GetInterventionFilesView.as_view(),
         name='get_intervention_files'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
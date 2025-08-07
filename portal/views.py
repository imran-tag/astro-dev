# portal/views.py
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .services.api_service import AstroAPIService
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.files.uploadedfile import InMemoryUploadedFile
import json
from django.urls import reverse
import time
import base64
from datetime import datetime
import io
import locale
from collections import defaultdict
from django.utils import timezone
import re # Import regex
import binascii # For handling base64 errors
import traceback # Pour les traces d'erreur détaillées
import sys # Pour les informations d'erreur système

INTERVENTION_STEPS = [
    'security_checklist',
    'photo_upload',
    'photos_after',
    'voice_recording',
    'comment',
    'quality_control',
    'signature'
]
# Helper function to clean potential API error messages
# Helper function to clean potential API error messages
def clean_api_message(api_response, default_message):
    message = default_message
    if api_response and isinstance(api_response, dict) and "message" in api_response:
        message = api_response["message"]
    # Remove any stray "success" word, case-insensitive
    message = re.sub(r"\bsuccess\b", "", message, flags=re.IGNORECASE).strip()
    # Correct common typo observed
    message = message.replace("2chec", "Échec")
    return message

# Fonction de journalisation améliorée
def log_debug(prefix, message, obj=None):
    """Fonction de journalisation améliorée qui affiche un préfixe, un message et optionnellement un objet"""
    print(f"DEBUG [{prefix}]: {message}")
    if obj is not None:
        if isinstance(obj, dict) or isinstance(obj, list):
            print(f"DEBUG [{prefix}] Object: {json.dumps(obj, default=str, indent=2)}")
        else:
            print(f"DEBUG [{prefix}] Object: {obj}")

class LoginView(View):
    template_name = 'portal/login.html'

    def get(self, request):
        if 'token' in request.session:
            return redirect('interventions')
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')

        api_service = AstroAPIService()
        response = api_service.login(email, password)

        if response and response.get('success'):
            request.session['token'] = response['token']
            request.session['user'] = {
                'uid': response['uid'],
                'email': response['email'],
                'firstname': response['firstname'],
                'lastname': response['lastname']
            }
            return redirect('interventions')
        else:
            messages.error(request, response.get('message', 'Login failed'))
            return render(request, self.template_name)


class InterventionListView(View):
    template_name = 'portal/interventions/list.html'

    # French month names
    FRENCH_MONTHS = {
        1: 'janvier',
        2: 'février',
        3: 'mars',
        4: 'avril',
        5: 'mai',
        6: 'juin',
        7: 'juillet',
        8: 'août',
        9: 'septembre',
        10: 'octobre',
        11: 'novembre',
        12: 'décembre'
    }

    # French day names
    FRENCH_DAYS = {
        0: 'lundi',
        1: 'mardi',
        2: 'mercredi',
        3: 'jeudi',
        4: 'vendredi',
        5: 'samedi',
        6: 'dimanche'
    }

    def format_date_in_french(self, date_obj):
        """Format a date in French."""
        day_name = self.FRENCH_DAYS[date_obj.weekday()]
        day_number = date_obj.day
        month_name = self.FRENCH_MONTHS[date_obj.month]
        year = date_obj.year
        return f"{day_name} {day_number} {month_name} {year}"

    def get(self, request):
        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']
        current_filter = request.GET.get('filter', 'all')

        # Get interventions
        interventions = api_service.get_interventions(token, user_uid, page=1)
        sorted_interventions = {}

        if interventions:
            # First apply status filtering
            if current_filter == 'planned':
                filtered_interventions = [i for i in interventions if i.get('status_uid') == '2']
            elif current_filter == 'in_progress':
                filtered_interventions = [i for i in interventions if i.get('status_uid') == '5']
            elif current_filter == 'completed':
                filtered_interventions = [i for i in interventions if i.get('status_uid') == '4']
            elif current_filter == 'not_validated':
                filtered_interventions = [i for i in interventions if i.get('status_uid') == '6']
            else:
                filtered_interventions = interventions  # Show all interventions

            # Separate urgent interventions
            urgent_interventions = [i for i in filtered_interventions if i.get('priority') == 'Urgente']
            if urgent_interventions:
                sorted_interventions['urgent'] = urgent_interventions

            # Handle regular interventions
            regular_interventions = [i for i in filtered_interventions if i.get('priority') != 'Urgente']

            # Group by date
            date_groups = {}
            today = datetime.now()
            today_str = today.strftime('%d/%m/%Y')

            for intervention in regular_interventions:
                intervention_date = intervention.get('date_time')
                # In views.py, change where you add today's interventions
                if intervention_date == today_str:
                    if 'today' not in sorted_interventions:  # Changed from 'aujourd\'hui'
                        sorted_interventions['today'] = []
                    sorted_interventions['today'].append(intervention)
                elif intervention_date:
                    try:
                        date_obj = datetime.strptime(intervention_date, '%d/%m/%Y').date()
                        if date_obj not in date_groups:
                            date_groups[date_obj] = []
                        date_groups[date_obj].append(intervention)
                    except ValueError as e:
                        print(f"Error parsing date for intervention {intervention.get('uid')}: {e}")
                        continue
            # Add this after defining regular_interventions
            for idx, intervention in enumerate(regular_interventions):
                print(f"Regular intervention {idx}:")
                print(f"  - priority: {intervention.get('priority')}")
                print(f"  - status_uid: {intervention.get('status_uid')}")
                print(f"  - date_time: {intervention.get('date_time')}")

                # Check if this date is being correctly grouped
                if intervention.get('date_time') == today_str:
                    print(f"  - This intervention should be in 'aujourd\\'hui' group")
                elif intervention.get('date_time'):
                    try:
                        date_obj = datetime.strptime(intervention.get('date_time'), '%d/%m/%Y').date()
                        french_date = self.format_date_in_french(date_obj)
                        print(f"  - This intervention should be in '{french_date}' group")
                    except Exception as e:
                        print(f"  - Error parsing date: {e}")

            # Add sorted date groups with French formatting
            for date in sorted(date_groups.keys()):
                french_date = self.format_date_in_french(date)
                sorted_interventions[french_date] = date_groups[date]

        return render(request, self.template_name, {
            'grouped_interventions': sorted_interventions,
            'current_filter': current_filter
        })


class InterventionDetailView(View):
    template_name = 'portal/interventions/detail.html'

    def get(self, request, intervention_id):
        print(f"DEBUG: Accessing detail view for intervention {intervention_id}")

        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get all interventions and find the specific one
        all_interventions = api_service.get_interventions(token, user_uid, page=1)

        if all_interventions:
            # Find the specific intervention
            intervention = next(
                (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                None
            )

            if intervention:
                return render(request, self.template_name, {
                    'intervention': intervention,
                    'google_maps_api_key': 'AIzaSyAKWcoD80ySGBa8O_Rx5Y8_4Bj1Er0Pcj4'
                })

        messages.error(request, 'Intervention non trouvée')
        return redirect('interventions')


@method_decorator(csrf_exempt, name='dispatch')
class InterventionUpdateStatusView(View):
    def post(self, request, intervention_id):
        if 'token' not in request.session:
            return JsonResponse({'success': False, 'message': 'Not authenticated'}, status=401)

        try:
            # No need to parse request body anymore since we're always setting to 'en_cours'
            api_service = AstroAPIService()
            result = api_service.update_intervention_status(
                request.session['token'],
                intervention_id,
                'en_cours'  # Status is hardcoded since we're always setting to 'en_cours'
            )

            if result:
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'Failed to update status'})

        except Exception as e:
            print(f"Error updating status: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SecurityChecklistView(View):
    template_name = 'portal/interventions/security_checklist.html'

    def get(self, request, intervention_id):
        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get all interventions and find the specific one
        all_interventions = api_service.get_interventions(token, user_uid, page=1)

        if all_interventions:
            intervention = next(
                (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                None
            )

            if intervention:
                # Check if status_uid is 5 (En cours)
                if intervention.get('status_uid') == '5':
                    # Get next step URL
                    current_step_index = INTERVENTION_STEPS.index('security_checklist')
                    next_step = INTERVENTION_STEPS[current_step_index + 1] if current_step_index + 1 < len(
                        INTERVENTION_STEPS) else None
                    next_url = reverse(next_step, kwargs={'intervention_id': intervention_id}) if next_step else None

                    return render(request, self.template_name, {
                        'intervention': intervention,
                        'security_items': [
                            'Lire les pièces jointes et informer son équipe',
                            'Mettre les EPI',
                            'Poser le matériel sur une protection'
                        ],
                        'next_url': next_url
                    })
                else:
                    messages.error(request, 'Cette intervention n\'est pas en cours')
                    return redirect('intervention_detail', intervention_id=intervention_id)

        messages.error(request, 'Intervention non trouvée')
        return redirect('interventions')

    def post(self, request, intervention_id):
        if 'token' not in request.session:
            return JsonResponse({'success': False, 'message': 'Not authenticated'})

        try:
            # Get next URL immediately
            current_step_index = INTERVENTION_STEPS.index('security_checklist')
            next_step = INTERVENTION_STEPS[current_step_index + 1]
            next_url = reverse(next_step, kwargs={'intervention_id': intervention_id})

            # Return success response immediately
            response = JsonResponse({
                'success': True,
                'next_url': next_url
            })

            # Background processing
            def save_in_background():
                api_service = AstroAPIService()
                token = request.session['token']
                security_data = request.POST.get('security', '')

                # Record start time using the dedicated endpoint
                time_response = api_service.update_intervention_time(
                    token=token,
                    intervention_id=intervention_id,
                    state='0'  # 1 indicates intervention start
                )

                if not time_response or time_response.get('code') != 1:
                    print(f"Failed to update start time: {time_response}")

                # Get current intervention data
                user_uid = request.session['user']['uid']
                all_interventions = api_service.get_interventions(token, user_uid, page=1)
                current_intervention = next(
                    (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                    None
                )

                if current_intervention:
                    # Save security checklist data
                    api_service.set_intervention_recap(
                        token=token,
                        intervention_id=intervention_id,
                        security=security_data,
                        quality=current_intervention.get('quality', ''),  # Keep existing quality data
                        images_before=current_intervention.get('images_before', ''),
                        images_after=current_intervention.get('images_after', ''),
                        comments=current_intervention.get('comments', ''),
                        signature=current_intervention.get('signature', ''),
                        items=current_intervention.get('items', ''),
                        video_before=current_intervention.get('video_before', ''),
                        status_uid=4
                    )

                    # Update status back to en_cours
                    api_service.update_intervention_status(
                        token=token,
                        intervention_id=intervention_id,
                        status='en_cours'
                    )

            # Start background task
            import threading
            thread = threading.Thread(target=save_in_background)
            thread.start()

            return response

        except Exception as e:
            print(f"Security checklist error: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            })

@method_decorator(csrf_exempt, name='dispatch')
class PhotoUploadView(View):
    template_name = 'portal/interventions/photo_upload.html'

    def get(self, request, intervention_id):
        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')
        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get fresh intervention data
        all_interventions = api_service.get_interventions(token, user_uid, page=1)

        if all_interventions:
            intervention = next(
                (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                None
            )

            if intervention:
                return render(request, self.template_name, {
                    'intervention': intervention,
                    'intervention_images': intervention.get('images_before', ''),
                })

        messages.error(request, 'Intervention non trouvée')
        return redirect('interventions')

    def post(self, request, intervention_id):
        if 'token' not in request.session:
            return JsonResponse({'success': False, 'message': 'Not authenticated'})

        api_service = AstroAPIService()
        token = request.session['token']

        try:
            # Check if this is a file upload request
            if 'file' in request.FILES:
                # Handle file upload
                upload_response = api_service.upload_media(
                    token,
                    request.FILES['file'],
                    intervention_id,
                    None
                )

                if not upload_response or upload_response.get('code') != '1':
                    return JsonResponse({'code': '0', 'message': 'Failed to upload file'})

                # Get the current intervention data to update images_before
                user_uid = request.session['user']['uid']
                all_interventions = api_service.get_interventions(token, user_uid, page=1)
                current_intervention = next(
                    (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                    None
                )

                if not current_intervention:
                    return JsonResponse({'code': '0', 'message': 'Intervention not found'})

                # Get current images and append new one
                current_images = current_intervention.get('images_before', '')
                new_image_path = upload_response.get('file_path', '')

                # Ensure new_image_path starts with /
                if new_image_path and not new_image_path.startswith('/'):
                    new_image_path = f"/{new_image_path}"

                if current_images:
                    # If we have existing images, make sure they all start with /
                    current_images_list = [
                        f"/{path.lstrip('/')}" if path.strip() else ""
                        for path in current_images.split(';')
                    ]
                    # Filter out empty strings and join with semicolons
                    current_images = ';'.join(filter(None, current_images_list))
                    updated_images = f"{current_images};{new_image_path}"
                else:
                    updated_images = new_image_path

                # Save using set_intervention_recap while preserving all other data
                recap_response = api_service.set_intervention_recap(
                    token=token,
                    intervention_id=intervention_id,
                    security=current_intervention.get('security', '1;1;1'),  # Preserve existing security data
                    quality=current_intervention.get('quality', ''),  # Preserve existing quality data
                    images_before=updated_images,  # Update images_before
                    images_after=current_intervention.get('images_after', ''),  # Preserve existing images_after
                    comments=current_intervention.get('comments', ''),  # Preserve existing comments
                    signature=current_intervention.get('signature', ''),  # Preserve existing signature
                    items=current_intervention.get('items', ''),  # Preserve existing items
                    video_before=current_intervention.get('video_before', ''),
                    status_uid=4  # Required for set_intervention_recap
                )

                if not recap_response or recap_response.get('code') != 1:
                    return JsonResponse({'code': '0', 'message': 'Failed to save image data'})

                # Restore status to en_cours (5)
                status_response = api_service.update_intervention_status(
                    token=token,
                    intervention_id=intervention_id,
                    status='en_cours'
                )

                if not status_response:
                    return JsonResponse({'code': '0', 'message': 'Failed to restore status'})

                return JsonResponse(upload_response)

            # This is a save request (SUIVANT button)
            else:
                # Get current intervention data
                user_uid = request.session['user']['uid']
                all_interventions = api_service.get_interventions(token, user_uid, page=1)
                current_intervention = next(
                    (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                    None
                )

                if not current_intervention:
                    return JsonResponse({'success': False, 'message': 'Intervention not found'})

                # Get images_before and ensure all paths start with /
                images_before = current_intervention.get('images_before', '')
                if images_before:
                    images_list = [
                        f"/{path.lstrip('/')}" if path.strip() else ""
                        for path in images_before.split(';')
                    ]
                    # Filter out empty strings and join with semicolons
                    images_before = ';'.join(filter(None, images_list))

                # Step 1: Save data using set_intervention_recap
                recap_response = api_service.set_intervention_recap(
                    token=token,
                    intervention_id=intervention_id,
                    security=current_intervention.get('security', '1;1;1'),  # Preserve existing security data
                    quality=current_intervention.get('quality', ''),  # Preserve existing quality data
                    images_before=images_before,  # Update images_before
                    images_after=current_intervention.get('images_after', ''),  # Preserve existing images_after
                    comments=current_intervention.get('comments', ''),  # Preserve existing comments
                    signature=current_intervention.get('signature', ''),  # Preserve existing signature
                    items=current_intervention.get('items', ''),  # Preserve existing items
                    video_before=current_intervention.get('video_before', ''),
                    status_uid=4
                )

                if not recap_response or recap_response.get('code') != 1:
                    return JsonResponse({
                        'success': False,
                        'message': 'Failed to save photos'
                    })

                # Step 2: Reset status to 5 (en_cours)
                status_response = api_service.update_intervention_status(
                    token=token,
                    intervention_id=intervention_id,
                    status='en_cours'
                )

                if not status_response:
                    return JsonResponse({
                        'success': False,
                        'message': 'Failed to restore intervention status'
                    })

                # Get next URL for navigation
                current_step_index = INTERVENTION_STEPS.index('photo_upload')
                next_step = INTERVENTION_STEPS[current_step_index + 1] if current_step_index + 1 < len(
                    INTERVENTION_STEPS) else None
                next_url = reverse(next_step, kwargs={'intervention_id': intervention_id}) if next_step else None

                return JsonResponse({
                    'success': True,
                    'next_url': next_url
                })

        except Exception as e:
            print(f"Photo upload error: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            })


@method_decorator(csrf_exempt, name='dispatch')
class PhotosAfterView(View):
    template_name = 'portal/interventions/photos_after.html'

    def get(self, request, intervention_id):
        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get fresh intervention data
        all_interventions = api_service.get_interventions(token, user_uid, page=1)

        if all_interventions:
            intervention = next(
                (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                None
            )

            if intervention:
                print(f"DEBUG: Intervention images_after: {intervention.get('images_after')}")  # Debug print

                # Get next step URL
                current_step_index = INTERVENTION_STEPS.index('photos_after')
                next_step = INTERVENTION_STEPS[current_step_index + 1] if current_step_index + 1 < len(
                    INTERVENTION_STEPS) else None
                next_url = reverse(next_step, kwargs={'intervention_id': intervention_id}) if next_step else None

                return render(request, self.template_name, {
                    'intervention': intervention,
                    'intervention_images': intervention.get('images_after', ''),
                    'next_url': next_url
                })

        messages.error(request, 'Intervention non trouvée')
        return redirect('interventions')

    def post(self, request, intervention_id):
        if 'token' not in request.session:
            return JsonResponse({'success': False, 'message': 'Not authenticated'})

        api_service = AstroAPIService()
        token = request.session['token']

        try:
            # Check if this is a file upload request
            if 'file' in request.FILES:
                # Handle file upload
                upload_response = api_service.upload_media(
                    token,
                    request.FILES['file'],
                    intervention_id,
                    None
                )

                if not upload_response or upload_response.get('code') != '1':
                    return JsonResponse({'code': '0', 'message': 'Failed to upload file'})

                # Get the current intervention data
                user_uid = request.session['user']['uid']
                all_interventions = api_service.get_interventions(token, user_uid, page=1)
                current_intervention = next(
                    (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                    None
                )

                if not current_intervention:
                    return JsonResponse({'code': '0', 'message': 'Intervention not found'})

                # Get current images and append new one
                current_images = current_intervention.get('images_after', '')
                new_image_path = upload_response.get('file_path', '')

                # Ensure new_image_path starts with /
                if new_image_path and not new_image_path.startswith('/'):
                    new_image_path = f"/{new_image_path}"

                if current_images:
                    # If we have existing images, make sure they all start with /
                    current_images_list = [
                        f"/{path.lstrip('/')}" if path.strip() else ""
                        for path in current_images.split(';')
                    ]
                    # Filter out empty strings and join with semicolons
                    current_images = ';'.join(filter(None, current_images_list))
                    updated_images = f"{current_images};{new_image_path}"
                else:
                    updated_images = new_image_path

                # Save using set_intervention_recap while preserving all other data
                recap_response = api_service.set_intervention_recap(
                    token=token,
                    intervention_id=intervention_id,
                    security=current_intervention.get('security', '1;1;1'),  # Preserve existing security data
                    quality=current_intervention.get('quality', ''),  # Preserve existing quality data
                    images_before=current_intervention.get('images_before', ''),  # Preserve existing images_before
                    images_after=updated_images,  # Update images_after
                    comments=current_intervention.get('comments', ''),  # Preserve existing comments
                    signature=current_intervention.get('signature', ''),  # Preserve existing signature
                    items=current_intervention.get('items', ''),  # Preserve existing items
                    video_before=current_intervention.get('video_before', ''),
                    status_uid=4  # Required for set_intervention_recap
                )

                if not recap_response or recap_response.get('code') != 1:
                    return JsonResponse({'code': '0', 'message': 'Failed to save image data'})

                # Restore status to en_cours (5)
                status_response = api_service.update_intervention_status(
                    token=token,
                    intervention_id=intervention_id,
                    status='en_cours'
                )

                if not status_response:
                    return JsonResponse({'code': '0', 'message': 'Failed to restore status'})

                return JsonResponse(upload_response)

            # This is a save request (SUIVANT button)
            else:
                # Get current intervention data
                user_uid = request.session['user']['uid']
                all_interventions = api_service.get_interventions(token, user_uid, page=1)
                current_intervention = next(
                    (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                    None
                )

                if not current_intervention:
                    return JsonResponse({'success': False, 'message': 'Intervention not found'})

                # Get images_after and ensure all paths start with /
                images_after = current_intervention.get('images_after', '')
                if images_after:
                    images_list = [
                        f"/{path.lstrip('/')}" if path.strip() else ""
                        for path in images_after.split(';')
                    ]
                    # Filter out empty strings and join with semicolons
                    images_after = ';'.join(filter(None, images_list))

                # Step 1: Save data using set_intervention_recap
                recap_response = api_service.set_intervention_recap(
                    token=token,
                    intervention_id=intervention_id,
                    security=current_intervention.get('security', '1;1;1'),  # Preserve existing security data
                    quality=current_intervention.get('quality', ''),  # Preserve existing quality data
                    images_before=current_intervention.get('images_before', ''),  # Preserve existing images_before
                    images_after=images_after,  # Update images_after
                    comments=current_intervention.get('comments', ''),  # Preserve existing comments
                    signature=current_intervention.get('signature', ''),  # Preserve existing signature
                    items=current_intervention.get('items', ''),  # Preserve existing items
                    video_before=current_intervention.get('video_before', ''),
                    status_uid=4
                )

                if not recap_response or recap_response.get('code') != 1:
                    return JsonResponse({
                        'success': False,
                        'message': 'Failed to save photos'
                    })

                # Step 2: Reset status to 5 (en_cours)
                status_response = api_service.update_intervention_status(
                    token=token,
                    intervention_id=intervention_id,
                    status='en_cours'
                )

                if not status_response:
                    return JsonResponse({
                        'success': False,
                        'message': 'Failed to restore intervention status'
                    })

                # Get next URL for navigation
                current_step_index = INTERVENTION_STEPS.index('photos_after')
                next_step = INTERVENTION_STEPS[current_step_index + 1] if current_step_index + 1 < len(
                    INTERVENTION_STEPS) else None
                next_url = reverse(next_step, kwargs={'intervention_id': intervention_id}) if next_step else None

                return JsonResponse({
                    'success': True,
                    'next_url': next_url
                })

        except Exception as e:
            print(f"Photos after upload error: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            })


@method_decorator(csrf_exempt, name='dispatch')
class CommentView(View):
    template_name = 'portal/interventions/comment.html'

    def get(self, request, intervention_id):
        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get fresh intervention data
        all_interventions = api_service.get_interventions(token, user_uid, page=1)

        if all_interventions:
            intervention = next(
                (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                None
            )

            if intervention:
                # Get next step URL
                current_step_index = INTERVENTION_STEPS.index('comment')
                next_step = INTERVENTION_STEPS[current_step_index + 1] if current_step_index + 1 < len(
                    INTERVENTION_STEPS) else None
                next_url = reverse(next_step, kwargs={'intervention_id': intervention_id}) if next_step else None

                return render(request, self.template_name, {
                    'intervention': intervention,
                    'next_url': next_url
                })

        messages.error(request, 'Intervention non trouvée')
        return redirect('interventions')

    def post(self, request, intervention_id):
        if 'token' not in request.session:
            return JsonResponse({'success': False, 'message': 'Not authenticated'})

        try:
            # Get next URL immediately
            current_step_index = INTERVENTION_STEPS.index('comment')
            next_step = INTERVENTION_STEPS[current_step_index + 1]
            next_url = reverse(next_step, kwargs={'intervention_id': intervention_id})

            # Return success response immediately
            response = JsonResponse({
                'success': True,
                'next_url': next_url
            })

            # Background processing
            def save_in_background():
                api_service = AstroAPIService()
                token = request.session['token']
                comment = request.POST.get('comment', '').strip()

                # Get current intervention data
                user_uid = request.session['user']['uid']
                all_interventions = api_service.get_interventions(token, user_uid, page=1)
                current_intervention = next(
                    (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                    None
                )

                if current_intervention:
                    # Save data
                    api_service.set_intervention_recap(
                        token=token,
                        intervention_id=intervention_id,
                        security=current_intervention.get('security', '1;1;1'),
                        quality=current_intervention.get('quality', ''),
                        images_before=current_intervention.get('images_before', ''),
                        images_after=current_intervention.get('images_after', ''),
                        comments=comment,
                        signature=current_intervention.get('signature', ''),
                        items=current_intervention.get('items', ''),
                        video_before=current_intervention.get('video_before', ''),
                        status_uid=4
                    )

                    # Restore status
                    api_service.update_intervention_status(
                        token=token,
                        intervention_id=intervention_id,
                        status='en_cours'
                    )

            # Start background task
            import threading
            thread = threading.Thread(target=save_in_background)
            thread.start()

            return response

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
@method_decorator(csrf_exempt, name='dispatch')
class QualityControlView(View):
    template_name = 'portal/interventions/quality_control.html'

    def get(self, request, intervention_id):
        if 'token' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        intervention = next(
            (i for i in api_service.get_interventions(token, user_uid, page=1)
             if str(i.get('uid')) == str(intervention_id)),
            None
        )

        if intervention:
            # Get next step URL
            current_step_index = INTERVENTION_STEPS.index('quality_control')
            next_step = INTERVENTION_STEPS[current_step_index + 1] if current_step_index + 1 < len(
                INTERVENTION_STEPS) else None
            next_url = reverse(next_step, kwargs={'intervention_id': intervention_id}) if next_step else None

            return render(request, self.template_name, {
                'intervention': intervention,
                'quality_items': [
                    'Ranger les outils',
                    'Nettoyer le chantier',
                    'Mise en pression des appareils sanitaires',
                    'Vérifier le gaz'
                ],
                'next_url': next_url
            })

        return redirect('interventions')

    def post(self, request, intervention_id):
        if 'token' not in request.session:
            return JsonResponse({'success': False, 'message': 'Not authenticated'})

        try:
            # Get next URL immediately
            current_step_index = INTERVENTION_STEPS.index('quality_control')
            next_step = INTERVENTION_STEPS[current_step_index + 1]
            next_url = reverse(next_step, kwargs={'intervention_id': intervention_id})

            # Return success response immediately
            response = JsonResponse({
                'success': True,
                'next_url': next_url
            })

            # Background processing
            def save_in_background():
                api_service = AstroAPIService()
                token = request.session['token']
                quality_data = request.POST.get('quality', '')

                # Get current intervention data
                user_uid = request.session['user']['uid']
                all_interventions = api_service.get_interventions(token, user_uid, page=1)
                current_intervention = next(
                    (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                    None
                )

                if current_intervention:
                    # Save data
                    api_service.set_intervention_recap(
                        token=token,
                        intervention_id=intervention_id,
                        security=current_intervention.get('security', '1;1;1'),
                        quality=quality_data,
                        images_before=current_intervention.get('images_before', ''),
                        images_after=current_intervention.get('images_after', ''),
                        comments=current_intervention.get('comments', ''),
                        signature=current_intervention.get('signature', ''),
                        items=current_intervention.get('items', ''),
                        video_before=current_intervention.get('video_before', ''),
                        status_uid=4
                    )

                    # Restore status
                    api_service.update_intervention_status(
                        token=token,
                        intervention_id=intervention_id,
                        status='en_cours'
                    )

            # Start background task
            import threading
            thread = threading.Thread(target=save_in_background)
            thread.start()

            return response

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })


@method_decorator(csrf_exempt, name="dispatch")
class SignatureView(View):
    template_name = "portal/interventions/signature.html"

    def get(self, request, intervention_id):
        if "token" not in request.session or "user" not in request.session:
            return redirect("login")
        api_service = AstroAPIService()
        token = request.session["token"]
        user_uid = request.session["user"]["uid"]

        all_interventions = api_service.get_interventions(token, user_uid, page=1)
        if all_interventions:
            intervention = next((i for i in all_interventions if str(i.get("uid")) == str(intervention_id)), None)
            if intervention:
                return render(request, self.template_name, {"intervention": intervention})
        messages.error(request, "Intervention non trouvée")
        return redirect("interventions")

    def post(self, request, intervention_id):
        if "token" not in request.session:
            return JsonResponse({"success": False, "message": "Non authentifié"}, status=401)

        api_service = AstroAPIService()
        token = request.session["token"]

        try:
            data = json.loads(request.body)
            log_debug("SIGNATURE", f"Requête POST reçue pour l'intervention {intervention_id}")
            log_debug("SIGNATURE", f"Clés dans les données: {list(data.keys())}")

            action = data.get("action")

            if action == "finish":
                log_debug("SIGNATURE", "Action: finish - Terminer l'intervention")
                # Action pour terminer l"intervention
                result = api_service.update_intervention_status(token, intervention_id,
                                                                "termine")  # Utilise le statut "termine"
                log_debug("SIGNATURE", "Résultat de update_intervention_status:", result)

                if result:
                    redirect_url = reverse("interventions")
                    return JsonResponse({"success": True, "redirect_url": redirect_url})
                else:
                    # Fournir un message d"erreur clair si la mise à jour du statut échoue
                    return JsonResponse({"success": False, "message": "Échec de la mise à jour du statut vers terminé"})

            elif action == "mark_not_validated":
                log_debug("SIGNATURE", "Action: mark_not_validated - Marquer comme non validée")
                # Action pour marquer comme non validée
                result = api_service.update_intervention_status(token, intervention_id, "non_validee")
                log_debug("SIGNATURE", "Résultat de update_intervention_status:", result)

                if result:
                    redirect_url = reverse("interventions")
                    return JsonResponse({"success": True, "redirect_url": redirect_url})
                else:
                    # Fournir un message d"erreur clair
                    return JsonResponse({"success": False, "message": "Échec du marquage comme non validée"})

            elif "signature" in data:
                # Action pour sauvegarder la signature (CORRECTED UPLOAD LOGIC)
                signature_data_url = data.get("signature")
                log_debug("SIGNATURE", "Action: Sauvegarde de signature")

                if not signature_data_url:
                    log_debug("SIGNATURE", "ERREUR: Données de signature manquantes")
                    return JsonResponse({"success": False, "message": "Données de signature manquantes"})

                if ";base64," not in signature_data_url:
                    log_debug("SIGNATURE", "ERREUR: Format de signature invalide, pas de marqueur base64")
                    return JsonResponse(
                        {"success": False, "message": "Format de signature invalide, pas de marqueur base64"})

                # Afficher les premiers caractères pour vérifier le format
                log_debug("SIGNATURE", f"Début des données de signature: {signature_data_url[:50]}...")

                try:
                    # 1. Decode base64 data URL
                    log_debug("SIGNATURE", "Étape 1: Décodage des données base64")
                    format, imgstr = signature_data_url.split(";base64,")
                    ext = format.split("/")[-1]
                    log_debug("SIGNATURE", f"Format détecté: {format}, extension: {ext}")

                    # Add padding if necessary
                    imgstr_padded = imgstr + "=" * (-len(imgstr) % 4)

                    # Essayer de décoder avec gestion d'erreur détaillée
                    try:
                        img_data = base64.b64decode(imgstr_padded)
                        log_debug("SIGNATURE", f"Décodage réussi, taille des données: {len(img_data)} octets")
                    except binascii.Error as padding_error:
                        log_debug("SIGNATURE", f"ERREUR de padding base64: {str(padding_error)}")
                        # Essayer sans padding
                        try:
                            img_data = base64.b64decode(imgstr)
                            log_debug("SIGNATURE", f"Décodage sans padding réussi, taille: {len(img_data)} octets")
                        except binascii.Error as no_padding_error:
                            log_debug("SIGNATURE", f"ERREUR de décodage sans padding: {str(no_padding_error)}")
                            # Dernière tentative avec des options plus permissives
                            try:
                                img_data = base64.b64decode(imgstr, validate=False)
                                log_debug("SIGNATURE",
                                          f"Décodage sans validation réussi, taille: {len(img_data)} octets")
                            except Exception as final_error:
                                log_debug("SIGNATURE", f"ÉCHEC FINAL du décodage: {str(final_error)}")
                                raise

                except (ValueError, binascii.Error) as decode_error:
                    error_detail = str(decode_error)
                    log_debug("SIGNATURE", f"ERREUR lors du décodage de la signature: {error_detail}")
                    log_debug("SIGNATURE", f"Traceback: {traceback.format_exc()}")
                    return JsonResponse({
                        "success": False,
                        "message": f"Erreur lors du décodage de la signature: {error_detail}"
                    })

                try:
                    # 2. Create an in-memory file object
                    log_debug("SIGNATURE", "Étape 2: Création du fichier en mémoire")
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    filename = f"signature_{intervention_id}_{timestamp}.{ext}"
                    log_debug("SIGNATURE", f"Nom du fichier: {filename}")

                    signature_file = InMemoryUploadedFile(
                        io.BytesIO(img_data),
                        None,  # field_name
                        filename,  # file name
                        f"image/{ext}",  # content_type
                        len(img_data),  # size
                        None  # charset
                    )
                    log_debug("SIGNATURE", "Fichier en mémoire créé avec succès")

                except Exception as file_creation_error:
                    error_detail = str(file_creation_error)
                    log_debug("SIGNATURE", f"ERREUR lors de la création du fichier: {error_detail}")
                    log_debug("SIGNATURE", f"Traceback: {traceback.format_exc()}")
                    return JsonResponse({
                        "success": False,
                        "message": f"Erreur lors de la création du fichier signature: {error_detail}"
                    })

                # 3. Upload the media file
                log_debug("SIGNATURE", "Étape 3: Téléversement du fichier via API")
                try:
                    upload_response = api_service.upload_media(token, signature_file)
                    log_debug("SIGNATURE", "Réponse du téléversement:", upload_response)
                except Exception as upload_error:
                    error_detail = str(upload_error)
                    log_debug("SIGNATURE", f"ERREUR lors du téléversement: {error_detail}")
                    log_debug("SIGNATURE", f"Traceback: {traceback.format_exc()}")
                    return JsonResponse({
                        "success": False,
                        "message": f"Erreur lors du téléversement de la signature: {error_detail}"
                    })

                # 4. Check upload response
                if not upload_response:
                    log_debug("SIGNATURE", "ERREUR: Réponse de téléversement vide")
                    return JsonResponse({
                        "success": False,
                        "message": "Aucune réponse reçue du serveur lors du téléversement"
                    })

                # CORRECTION: Comparer avec "1" (chaîne) au lieu de 1 (entier)
                if upload_response.get("code") != "1":
                    error_msg = clean_api_message(upload_response, "Échec du téléversement de la signature")
                    log_debug("SIGNATURE", f"ERREUR: Code de réponse non-succès: {upload_response.get('code')}")
                    log_debug("SIGNATURE", f"Message d'erreur: {error_msg}")
                    return JsonResponse({"success": False, "message": error_msg})

                # Utiliser le chemin du fichier retourné par l'API
                file_path = upload_response.get("file_path")
                if not file_path:
                    log_debug("SIGNATURE", "ERREUR: Chemin de fichier manquant dans la réponse")
                    return JsonResponse({
                        "success": False,
                        "message": "Erreur interne: Chemin de signature manquant après téléversement"
                    })

                log_debug("SIGNATURE", f"Téléversement réussi, chemin du fichier: {file_path}")

                # 5. Get current intervention data
                log_debug("SIGNATURE", "Étape 4: Récupération des données d'intervention actuelles")
                try:
                    user_uid = request.session["user"]["uid"]
                    all_interventions = api_service.get_interventions(token, user_uid, page=1)
                    current_intervention = next(
                        (i for i in all_interventions if str(i.get("uid")) == str(intervention_id)), None)
                except Exception as get_intervention_error:
                    error_detail = str(get_intervention_error)
                    log_debug("SIGNATURE", f"ERREUR lors de la récupération de l'intervention: {error_detail}")
                    log_debug("SIGNATURE", f"Traceback: {traceback.format_exc()}")
                    return JsonResponse({
                        "success": False,
                        "message": f"Erreur lors de la récupération des données d'intervention: {error_detail}"
                    })

                if not current_intervention:
                    log_debug("SIGNATURE", f"ERREUR: Intervention {intervention_id} non trouvée")
                    return JsonResponse({"success": False, "message": "Intervention non trouvée pour la mise à jour"})

                # 6. Update intervention recap with file path
                log_debug("SIGNATURE", "Étape 5: Mise à jour de l'intervention avec le chemin de signature")
                log_debug("SIGNATURE",
                          f"Valeurs actuelles de l'intervention: security={current_intervention.get('security', '[vide]')}, quality={current_intervention.get('quality', '[vide]')}, signature={current_intervention.get('signature', '[vide]')}")

                try:
                    recap_response = api_service.set_intervention_recap(
                        token=token,
                        intervention_id=intervention_id,
                        security=current_intervention.get("security", ""),
                        quality=current_intervention.get("quality", ""),
                        images_before=current_intervention.get("images_before", ""),
                        images_after=current_intervention.get("images_after", ""),
                        comments=current_intervention.get("comments", ""),
                        signature=file_path,  # CORRECTION: Utiliser le chemin du fichier au lieu de l'UID
                        items=current_intervention.get("items", ""),
                        video_before=current_intervention.get("video_before", ""),
                        status_uid=current_intervention.get("status_uid", "5")  # Keep current status
                    )
                    log_debug("SIGNATURE", "Réponse de la mise à jour recap:", recap_response)
                except Exception as recap_error:
                    error_detail = str(recap_error)
                    log_debug("SIGNATURE", f"ERREUR lors de la mise à jour recap: {error_detail}")
                    log_debug("SIGNATURE", f"Traceback: {traceback.format_exc()}")
                    return JsonResponse({
                        "success": False,
                        "message": f"Erreur lors de la mise à jour de l'intervention avec la signature: {error_detail}"
                    })

                # 7. Check recap update response
                if not recap_response:
                    log_debug("SIGNATURE", "ERREUR: Réponse de mise à jour recap vide")
                    return JsonResponse({
                        "success": False,
                        "message": "Aucune réponse reçue du serveur lors de la mise à jour de l'intervention"
                    })

                # CORRECTION: Comparer avec "1" (chaîne) au lieu de 1 (entier)
                if str(recap_response.get("code")) == "1" or recap_response.get("code") == 1:
                    log_debug("SIGNATURE", "SUCCÈS: Signature sauvegardée avec succès")
                    return JsonResponse({"success": True})
                else:
                    error_msg = clean_api_message(recap_response, "Échec de la sauvegarde de la référence de signature")
                    log_debug("SIGNATURE", f"ERREUR: Code de réponse non-succès: {recap_response.get('code')}")
                    log_debug("SIGNATURE", f"Message d'erreur: {error_msg}")
                    return JsonResponse({"success": False, "message": error_msg})

            else:
                log_debug("SIGNATURE",
                          f"ERREUR: Action invalide ou données manquantes. Clés disponibles: {list(data.keys())}")
                return JsonResponse({"success": False, "message": "Action invalide ou données manquantes"})

        except json.JSONDecodeError as json_error:
            log_debug("SIGNATURE", f"ERREUR JSON: {str(json_error)}")
            return JsonResponse({"success": False, "message": "Données JSON invalides"}, status=400)
        except Exception as e:
            # Catch-all for unexpected errors during the process
            error_detail = str(e)
            log_debug("SIGNATURE", f"ERREUR INATTENDUE: {error_detail}")
            log_debug("SIGNATURE", f"Type d'erreur: {type(e).__name__}")
            log_debug("SIGNATURE", f"Traceback: {traceback.format_exc()}")

            # Récupérer les informations système
            exc_type, exc_value, exc_traceback = sys.exc_info()
            log_debug("SIGNATURE", f"Exception type: {exc_type}")
            log_debug("SIGNATURE", f"Exception value: {exc_value}")

            return JsonResponse({
                "success": False,
                "message": f"Erreur lors du traitement de la signature: {error_detail}",
                "error_type": type(e).__name__
            }, status=500)



class GetInterventionFilesView(View):
    def get(self, request, intervention_id):
        if 'token' not in request.session:
            return JsonResponse({'success': False, 'message': 'Not authenticated'})

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get intervention
        all_interventions = api_service.get_interventions(token, user_uid, page=1)
        intervention = next(
            (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
            None
        )

        if intervention:
            # Get files from the files_urls field
            files = []
            if intervention.get('files_urls'):
                files = [url.strip() for url in intervention['files_urls'].split(';') if url.strip()]

            return JsonResponse({
                'success': True,
                'files': files
            })

        return JsonResponse({
            'success': False,
            'message': 'Intervention not found'
        })



@method_decorator(csrf_exempt, name='dispatch')
class VoiceRecordingView(View):
    template_name = 'portal/interventions/voice_recording.html'

    def get(self, request, intervention_id):
        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get fresh intervention data
        all_interventions = api_service.get_interventions(token, user_uid, page=1)

        if all_interventions:
            intervention = next(
                (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                None
            )

            if intervention:
                # Get next step URL
                current_step_index = INTERVENTION_STEPS.index('voice_recording')
                next_step = INTERVENTION_STEPS[current_step_index + 1] if current_step_index + 1 < len(
                    INTERVENTION_STEPS) else None
                next_url = reverse(next_step, kwargs={'intervention_id': intervention_id}) if next_step else None

                return render(request, self.template_name, {
                    'intervention': intervention,
                    'next_url': next_url
                })

        messages.error(request, 'Intervention non trouvée')
        return redirect('interventions')

    def post(self, request, intervention_id):
        if 'token' not in request.session:
            return JsonResponse({'success': False, 'message': 'Not authenticated'})

        try:
            api_service = AstroAPIService()
            token = request.session['token']

            # Check if this is a file upload request
            if 'audio_blob' in request.FILES:
                # Handle audio file upload
                upload_response = api_service.upload_media(
                    token,
                    request.FILES['audio_blob'],
                    intervention_id,
                    None
                )

                if not upload_response or upload_response.get('code') != '1':
                    return JsonResponse({'code': '0', 'message': 'Failed to upload audio'})

                # Get the current intervention data
                user_uid = request.session['user']['uid']
                all_interventions = api_service.get_interventions(token, user_uid, page=1)
                current_intervention = next(
                    (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                    None
                )

                if not current_intervention:
                    return JsonResponse({'code': '0', 'message': 'Intervention not found'})

                # Get new audio path
                new_audio_path = upload_response.get('file_path', '')
                if new_audio_path and not new_audio_path.startswith('/'):
                    new_audio_path = f"/{new_audio_path}"

                # Save using set_intervention_recap
                recap_response = api_service.set_intervention_recap(
                    token=token,
                    intervention_id=intervention_id,
                    security=current_intervention.get('security', '1;1;1'),
                    quality=current_intervention.get('quality', ''),
                    images_before=current_intervention.get('images_before', ''),
                    images_after=current_intervention.get('images_after', ''),
                    comments=current_intervention.get('comments', ''),
                    signature=current_intervention.get('signature', ''),
                    items=current_intervention.get('items', ''),
                    video_before=new_audio_path,  # Save audio in video_before
                    status_uid=4
                )

                if not recap_response or recap_response.get('code') != 1:
                    return JsonResponse({'code': '0', 'message': 'Failed to save audio data'})

                # Restore status to en_cours (5)
                status_response = api_service.update_intervention_status(
                    token=token,
                    intervention_id=intervention_id,
                    status='en_cours'
                )

                if not status_response:
                    return JsonResponse({'code': '0', 'message': 'Failed to restore status'})

                return JsonResponse({
                    'success': True,
                    'next_url': reverse('comment', kwargs={'intervention_id': intervention_id})
                })

            return JsonResponse({'success': False, 'message': 'No audio file provided'})

        except Exception as e:
            print(f"Voice recording error: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            })




class LogoutView(View):
    def get(self, request):
        request.session.flush()
        return redirect('login')
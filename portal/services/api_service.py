# portal/services/api_service.py
import requests
from _datetime import datetime, timedelta


class AstroAPIService:
    def __init__(self):
        self.base_url = "https://astro-tech.fr/astro-ges"

    def login(self, email, password):
        """Authenticate user with astro API"""
        try:
            url = f"{self.base_url}/api/sign_in"

            data = {
                "type": "email",
                "email": email,
                "password": password
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "*/*"
            }

            response = requests.post(url, data=data, headers=headers)

            print("Response status:", response.status_code)  # Debug print
            if response.status_code == 200:
                json_response = response.json()
                if json_response.get("code") == 1:
                    return {
                        "success": True,
                        "token": json_response.get("token"),
                        "uid": json_response.get("uid"),
                        "email": json_response.get("email"),
                        "firstname": json_response.get("firstname"),
                        "lastname": json_response.get("lastname")
                    }
                else:
                    return {
                        "success": False,
                        "message": json_response.get("message")
                    }

        except Exception as e:
            print(f"Login error: {str(e)}")
            return {"success": False, "message": "Connection error"}

    def get_interventions(self, token, user_uid, page=1):
        try:
            url = f"{self.base_url}/api/get_interventions"

            data = {
                "token": token,
                "user_uid": user_uid,
                "page": page
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "*/*"
            }

            response = requests.post(url, data=data, headers=headers)
            print(f"Interventions response status: {response.status_code}")  # Debug print

            if response.status_code == 200:
                json_response = response.json()
                if json_response.get("code") == 1:
                    return json_response.get("interventions", [])
                print(f"API error response: {json_response}")
            return []  # Return empty list instead of None
        except Exception as e:
            print(f"Get interventions error: {str(e)}")
            return []  # Return empty list instead of None

    def update_intervention_status(self, token, intervention_id, status):
        """Update intervention status"""
        try:
            url = f"{self.base_url}/api/update_intervention_status"

            # Convert status string to status_uid
            status_uid = "5"  # default for 'en_cours'
            if status == "non_validee":
                status_uid = "6"
            elif status == "termine":  # Ajout de la condition pour le statut terminé
                status_uid = "4"

            data = {
                "token": token,
                "uid": intervention_id,
                "status_uid": status_uid
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "*/*"
            }

            print(f"Sending status update request: {data}")  # Debug print
            response = requests.post(url, data=data, headers=headers)
            print(f"Status update response: {response.text}")  # Debug print

            if response.status_code == 200:
                json_response = response.json()
                return json_response.get("code") == 1

            return False

        except Exception as e:
            print(f"Update status error: {str(e)}")
            return False

    # api_service.py
    def update_intervention_images(self, token, intervention_id, images_before, current_intervention):
        """Update intervention's images without changing status"""
        try:
            # Change to a different endpoint that only updates images
            url = f"{self.base_url}/api/update_intervention_images"

            data = {
                "token": token,
                "uid": intervention_id,
                "images_before": images_before,
                "status_uid": current_intervention.get("status_uid", "5")  # Keep current status
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "*/*"
            }

            print(f"Updating intervention images with data for before:", data)  # Debug print
            response = requests.post(url, data=data, headers=headers)
            print(f"Update response for before: {response.text}")  # Debug print

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            print(f"Update intervention error: {str(e)}")
            return None

    def update_intervention_images_after(self, token, intervention_id, images_after, current_intervention):
        """Update intervention's after images without changing status"""
        try:
            url = f"{self.base_url}/api/update_intervention_images"

            data = {
                "token": token,
                "uid": intervention_id,
                "images_after": images_after,
                "status_uid": current_intervention.get("status_uid", "5")  # Keep current status
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "*/*"
            }

            print(f"Updating intervention after images with data for after:", data)  # Debug print
            response = requests.post(url, data=data, headers=headers)
            print(f"Update response for after: {response.text}")  # Debug print

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            print(f"Update intervention error: {str(e)}")
            return None

    # portal/services/api_service.py
    # api_service.py
    def upload_media(self, token, file, intervention_id=None, current_intervention=None):
        """Upload media file"""
        try:
            url = f"{self.base_url}/api/add_media"

            files = {
                "file": (file.name, file, file.content_type)
            }
            data = {
                "token": token
            }

            print(f"Uploading file with data:", data)  # Debug print
            response = requests.post(url, files=files, data=data)
            print(f"Upload response: {response.text}")  # Debug print

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            print(f"Upload media error: {str(e)}")
            return None

    # api_service.py
    def set_intervention_recap(self, token, intervention_id, security, quality, images_before, images_after, comments,
                               signature, items, video_before, status_uid):
        """Complete intervention with all final data"""
        try:
            url = f"{self.base_url}/api/set_intervention_recap"

            data = {
                "token": token,
                "uid": intervention_id,
                "security": security,
                "quality": quality,
                "images_before": images_before,
                "images_after": images_after,
                "comments": comments,
                "signature": signature,
                "items": items,
                "video_before": video_before,
                "status_uid": status_uid
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "*/*"
            }

            print(f"Sending recap data:", data)  # Debug print
            response = requests.post(url, data=data, headers=headers)
            print(f"Recap response: {response.text}")  # Debug print

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception as e:
                    print(f"Error parsing JSON response: {str(e)}")
                    return None
            return None

        except Exception as e:
            print(f"Set recap error: {str(e)}")
            return None

    def update_intervention_time(self, token, intervention_id, state):
        """Update intervention time
        state:
        1 = Intervention start
        2 = Intervention picture before
        3 = Intervention picture after
        """
        try:
            url = f"{self.base_url}/api/update_intervention_time"

            current_time = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

            data = {
                "token": token,
                "uid": intervention_id,
                "state": state,  # 1 for start time
                "data": current_time
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "*/*"
            }

            print(f"Updating intervention time with data:", data)  # Debug print
            response = requests.post(url, data=data, headers=headers)
            print(f"Time update response: {response.text}")  # Debug print

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            print(f"Update time error: {str(e)}")
            return None


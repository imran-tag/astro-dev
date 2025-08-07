# technician/portal/config.py
class APIEndpoints:
    BASE_URL = "http://astro-tech.fr/astro-ges/api"  # Replace with your actual URL

    # Auth endpoints
    SIGN_IN = f"{BASE_URL}/sign_in.php"
    SET_TECHNICIAN_TOKEN = f"{BASE_URL}/set_technician_token.php"

    # Intervention endpoints
    GET_INTERVENTIONS = f"{BASE_URL}/get_interventions.php"
    UPDATE_INTERVENTION_STATUS = f"{BASE_URL}/update_intervention_status.php"
    UPDATE_INTERVENTION_TIME = f"{BASE_URL}/update_intervention_time.php"
    SET_INTERVENTION_RECAP = f"{BASE_URL}/set_intervention_recap.php"
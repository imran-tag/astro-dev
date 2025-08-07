# portal/utils.py
import base64
import os
import time


def save_base64_file(base64_data, filename):
    """Save base64 data as file"""
    try:
        # Remove header if present
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]

        # Decode base64
        file_data = base64.b64decode(base64_data)

        # Ensure directory exists
        os.makedirs('uploads/files/interventions', exist_ok=True)

        # Full path
        file_path = f'uploads/files/interventions/{filename}'

        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_data)

        return file_path
    except Exception as e:
        print(f"Error saving file: {str(e)}")
        return None
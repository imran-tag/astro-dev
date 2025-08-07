import os
import sys


def log_error(message):
    with open('/home/astrotec/public_html/mon.astro-tech.fr/error.log', 'a') as f:
        f.write(f"{message}\n")


try:
    log_error("Starting application...")

    # Add paths
    base_dir = '/home/astrotec/public_html/mon.astro-tech.fr'
    venv_dir = '/home/astrotec/myenv/lib/python3.11/site-packages'

    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    if venv_dir not in sys.path:
        sys.path.insert(1, venv_dir)

    log_error(f"Python path: {sys.path}")

    # Set Django settings
    os.environ['DJANGO_SETTINGS_MODULE'] = 'technician.settings'
    log_error("Settings module set")

    # Initialize Django
    from django.core.wsgi import get_wsgi_application

    log_error("Imported get_wsgi_application")

    application = get_wsgi_application()
    log_error("Application initialized")

except Exception as e:
    log_error(f"Error: {str(e)}")


    def application(environ, start_response):
        status = '500 Internal Server Error'
        response_headers = [('Content-Type', 'text/plain')]
        start_response(status, response_headers)
        return [f"Application Error: {str(e)}".encode()]
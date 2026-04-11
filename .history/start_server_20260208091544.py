import os
from waitress import serve

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.wsgi import application

if __name__ == "__main__":
    serve(application, host="127.0.0.1", port=8000)

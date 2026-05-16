import os
import sys
import django
from pathlib import Path


def get_rows():
    Chats = django.apps.apps.get_model('app_views', 'Chats')
    return list(Chats.objects.all())

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parents[1]
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myApp.settings")
    django.setup()
    rows = get_rows()
    for row in rows:
        print(row.model_response)
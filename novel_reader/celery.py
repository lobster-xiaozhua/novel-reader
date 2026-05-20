import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'novel_reader.settings')

app = Celery('novel_reader')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

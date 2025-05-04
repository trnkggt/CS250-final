import os

from celery import Celery
from app.core import settings


celery = Celery(__name__,
                broker=settings.CELERY_BROKER_URL,
                backend=settings.CELERY_BACKEND_URL)


celery.autodiscover_tasks(['app.tasks'])
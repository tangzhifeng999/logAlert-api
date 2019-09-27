from celery import Celery
from config import CELERY_REDIS_HOST, CELERY_REDIS_PASSWORD, CELERY_REDIS_PORT, CELERY_REDIS_DB


CELERY_CONFIG = {
    'CELERY_BROKER_URL': 'redis://:' + CELERY_REDIS_PASSWORD + '@' + CELERY_REDIS_HOST + ':' + CELERY_REDIS_PORT + '/' + CELERY_REDIS_DB,
    'CELERYD_FORCE_EXECV': True,
    'CELERY_CREATE_MISSING_QUEUES': True,
    'CELERY_IMPORTS': ['info.celery_task.tasks'],
    'CELERY_TIMEZONE': "Asia/Shanghai"
}

logAlertCelery = Celery('tasks', broker=CELERY_CONFIG['CELERY_BROKER_URL'])
logAlertCelery.conf.update(CELERY_CONFIG)
logAlertCelery.config_from_object('info.celery_task.celeryconfig')

celery -A info.celery_task.make_celery.logAlertCelery beat &
celery -A info.celery_task.make_celery.logAlertCelery worker -f $LOG_PATH --loglevel=DEBUG -P eventlet -c 1000 &
gunicorn app:app -k gevent -b 0.0.0.0:5005 --log-file /var/log/logAlert/log.log --log-level DEBUG
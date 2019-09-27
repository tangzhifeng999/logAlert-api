from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    # 月度统计通知相关责任人，celery去做。
    'monthly_report_email': {
        'task': 'monthly_report_email',
        'schedule': crontab(minute='30', hour='09', day_of_month='1')
    }
}

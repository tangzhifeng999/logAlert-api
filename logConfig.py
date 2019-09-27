# -*- coding:utf-8 -*-
import os
import logging.config
from config import LOGGING_LEVEL
import logging

env_dist = os.environ
# 这里用了环境变量。也可以写配置文件。按实际要求来。不过以后一些配置会往环境变量走
log_path = env_dist.get('LOG_PATH', '/var/log/logAlert/log.log')

LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s'
        }
    },
    'handlers': {
        'celery': {
            'level': LOGGING_LEVEL,
            'formatter': 'simple',
            'class': 'cloghandler.ConcurrentRotatingFileHandler',
            'filename': log_path,
            'encoding': 'utf-8',
            'maxBytes': 1024 * 1024 * 10,  # 当达到10MB时分割日志
            'backupCount': 10,  # 最多保留10份文件
            'delay': True,  # If delay is true, file opening is deferred until the first
        },
    },
    'loggers': {
        'myapp': {
            'handlers': ['celery'],
            'level': LOGGING_LEVEL,
            'propagate': False,
        },
        '': {
            'handlers': ['celery'],
            'level': LOGGING_LEVEL,
            'propagate': False,
        }
    }
}
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger('myapp')


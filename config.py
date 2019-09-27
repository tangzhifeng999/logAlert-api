from redis import StrictRedis


"""
    需要说明的是，项目里面有了config和config.prod 来区分不同环境下的配置，这个是第一个项目，不知道这个架子就自己瞎写的，后来懒得修改了，
    然后就是现在这个破样子了。
"""

redis_store = StrictRedis(host='redis_host', port=6666)
MONGO_URL = 'mongo_url'
EMAIL = 'email_host'

# celery任务
CELERY_REDIS_HOST = 'redis_hoot'
CELERY_REDIS_PASSWORD = 'redis_password'
CELERY_REDIS_PORT = 'redis_port'
CELERY_REDIS_DB = 'redis_db'


class Config():
    # 配置密钥
    SECRET_KEY = '这里是密钥信息'


class DevelopmentConfig(Config):
    # 配置session信息存储位置,实现状态保持.
    SESSION_TYPE = 'redis'
    REDIS_HOST = 'redis_host'
    REDIS_PASSWORD = 'redis_password'
    REDIS_PORT = 'redis_port'
    SESSION_REDIS = StrictRedis(host=REDIS_HOST, password=REDIS_PASSWORD, port=REDIS_PORT)
    # session有限期
    PERMANENT_SESSION_LIFTTIME = 86400


class ProductionConfig(Config):
    SESSION_TYPE = 'redis'
    REDIS_HOST = 'redis_host'
    REDIS_PASSWORD = 'redis_password'
    REDIS_PORT = 'redis_port'
    SESSION_REDIS = StrictRedis(host=REDIS_HOST, password=REDIS_PASSWORD, port=REDIS_PORT)
    PERMANENT_SESSION_LIFTTIME = 86400


LOGGING_LEVEL = 'DEBUG'

config_dict = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}

ENV = 'development'



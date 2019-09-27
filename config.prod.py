from redis import StrictRedis


MONGO_URL = "mongo_url"
EMAIL = 'email_url'

"""
    这里和config的配置有很多重复的地方，建议直接在config和config.prod中直接写配置就好了。
"""
CELERY_REDIS_HOST = 'redis_host'
CELERY_REDIS_PASSWORD = 'redis_password'
CELERY_REDIS_PORT = 'redis_port'
CELERY_REDIS_DB = 'redis_db'


class Config():
    # 配置密钥
    SECRET_KEY = 'secret_key'


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

ENV = 'production'



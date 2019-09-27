from flask import Flask
from config import config_dict
from flask_session import Session
from info.login import login_blue
from info.controller import log_blue
from info.user import user_blue
from info.project import project_blue
from info.count import count_blue
from flask_apscheduler import APScheduler
from info.tasks.control_process.tasks import control_process
from info.utils.common import initialize
from info.home import home_blue


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config_dict[config_name])
    Session(app)
    # 登录
    app.register_blueprint(login_blue)
    # 错误日志
    app.register_blueprint(log_blue)
    # 用户
    app.register_blueprint(user_blue)
    # 项目
    app.register_blueprint(project_blue)
    # 统计
    app.register_blueprint(count_blue)
    # 首页
    app.register_blueprint(home_blue)
    # 初始化函数，在项目重新启动的时候做一下初始化工作，将重启之前仍运行的进程杀死，然后进程号清除，以便重新启动。
    initialize()
    # 定时任务，每1min对数据库监控，找出来需要启动的监控任务，关闭需要关闭的监控任务。
    scheduler = APScheduler()
    scheduler.init_app(app=app)
    scheduler.add_job("999", control_process, trigger='interval', seconds=60, max_instances=9999)
    scheduler.start()
    # 注意，定时任务默认是不会在项目部署的时候启动，搜索可能是因为是部署服务器默认是one thread one process，没有请求的时候，部分进程被挂起。
    return app

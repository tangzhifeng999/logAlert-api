from __future__ import absolute_import
from info.celery_task.make_celery import logAlertCelery
from celery.utils.log import get_task_logger
import json, requests, time
from config import EMAIL
import mongodb
from info.utils.common import get_last_month_date
from config import ENV
import prettytable as pt


logger = get_task_logger('myapp')


def get_person_email_list():
    """
    根据配置项目的接受人统计出月报发送人的邮箱列表
    :return:
    """
    receiver = []
    tasks = mongodb.TASK.find({'type': 1})
    for task in tasks:
        person_list = task.get('person')
        for person in person_list:
            user_info = mongodb.USER.find_one({'name': person})
            email = user_info.get('email')
            if email not in receiver:
                receiver.append(email)
    return receiver


def get_all_person_email_list():
    """
    获取系统中所有活跃的用户
    :return:
    """
    receiver = [user.get('email') for user in mongodb.USER.find({"status": True})]
    return receiver


@logAlertCelery.task(name="monthly_report_email")
def monthly_report_email():
    # 月报统计，统计已经配置的项目的告警日志产生数目，开发人员确认的告警数，完成的告警数，设置为不再告警的数目。
    if ENV == 'development':
        receiver = ['tzf@yuxisoft.cn']   # 统计的项目的设置的项目负责人邮件地址列表
    else:
        receiver = get_all_person_email_list()
    last_mon_start_date, last_mon_end_date = get_last_month_date()
    tm_year = last_mon_start_date.split('.')[0]
    tm_mon = last_mon_start_date.split('.')[1]
    content = '{}年{}月份日志告警信息统计结果如下:\n\n'.format(tm_year, tm_mon)
    content = content + '-------------------------------------------------------------------------------------' \
                        '-----------------------------------\n'
    project_list = list(mongodb.PROJECT.find())
    a = []
    for project in project_list:
        array = []
        project_name = project.get('name')
        project_app = project.get('app')
        content = content + '项目名称:【{}】,项目代号:【{}】\n'.format(project_name, project_app)
        log_info_total_num = mongodb.LOGINFO.find({'app': project_app, 'update_time': {'$gte': last_mon_start_date, '$lte': last_mon_end_date}}).count()
        api_log_num = mongodb.LOGINFO.find({'app': project_app, 'type': 'apilog',
                                            'update_time': {'$gte': last_mon_start_date, '$lte': last_mon_end_date}}).count()
        nginx_access_num = mongodb.LOGINFO.find({'app': project_app, 'type': 'nginx-access',
                                                 'update_time': {'$gte': last_mon_start_date, '$lte': last_mon_end_date}}).count()
        content = content + '    ·告警信息总条数:{}条，其中，apilog类型告警日志数目:{}条, nginx-access' \
                            '类型告警日志数目:{}条\n'.format(log_info_total_num, api_log_num, nginx_access_num)
        api_log_solve_num = mongodb.LOGINFO.find({'app': project_app, 'type': 'apilog', 'status': {'$in': [2, 3]},
                                                  'update_time': {'$gte': last_mon_start_date, '$lte': last_mon_end_date}}).count()
        api_log_not_solve_num = api_log_num - api_log_solve_num
        if api_log_num:
            api_log_solve_percentage = '%.2f%%' % ((api_log_solve_num / api_log_num) * 100)
        else:
            api_log_solve_percentage = '100%'
        content = content + '   ·apilog类型的告警日志已完成处理数:{},未完成处理数:{},完成率:{}\n'.format(api_log_solve_num,
                                                            api_log_not_solve_num, api_log_solve_percentage)
        nginx_access_solve_num = mongodb.LOGINFO.find({'app': project_app, 'type': 'nginx-access', 'status': {'$in': [2, 3]},
                                                       'update_time': {'$gte': last_mon_start_date, '$lte': last_mon_end_date}}).count()
        nginx_access_not_solve_num = nginx_access_num - nginx_access_solve_num
        if nginx_access_num:
            nginx_access_solve_percentage = '%.2f%%' % ((nginx_access_solve_num / nginx_access_num) * 100)
        else:
            nginx_access_solve_percentage = '100%'
        content = content + '   ·nginx-access类型的告警日志已完成处理数:{},未完成处理数:{},完成率:{}\n'.format(nginx_access_solve_num,
                                                            nginx_access_not_solve_num, nginx_access_solve_percentage)
        log_info_total_solve_num = mongodb.LOGINFO.find({'app': project_app, 'status': {'$in': [2, 3]},
                                                 'update_time': {'$gte': last_mon_start_date, '$lte': last_mon_end_date}}).count()
        log_info_total_not_solve_num = log_info_total_num - log_info_total_solve_num
        if log_info_total_num:
            log_info_total_solve_percentage = '%.2f%%' % ((log_info_total_solve_num / log_info_total_num) * 100)
        else:
            log_info_total_solve_percentage = '100%'
        content = content + '【{}】项目本月已解决告警问题数:{},未解决告警问题数:{},总完成率:{}\n'.format(project_name,
                                                                               log_info_total_solve_num,
                                                                               log_info_total_not_solve_num,
                                                                               log_info_total_solve_percentage)
        content = content + '-------------------------------------------------------------------------------------' \
                        '-----------------------------------\n'
        array.append(project_app)
        array.append(log_info_total_num)
        array.append(api_log_solve_num + nginx_access_solve_num)
        array.append(api_log_not_solve_num + nginx_access_not_solve_num)
        array.append(log_info_total_solve_percentage)
        a.append(array)
    tb = pt.PrettyTable()
    # tb.horizontal_char = '一'
    tb.field_names = ["name", "total", "finished", "notFinished", "per"]
    for one in a:
        tb.add_row(one)
    tb = str(tb)
    content = tb + '\n\n\n' + content
    # return content
    date_dict = {
        "title": "告警日志信息统计月报",
        "content": content,
        "receiver": receiver
    }
    date_json = json.dumps(date_dict)
    flag = 1
    while True and flag <= 2:
        headers = {
            'Content-Type': 'application/json'
        }
        resp = requests.post(EMAIL, headers=headers, data=date_json)
        resp.encoding = 'utf-8'
        respstr = json.loads(resp.text)
        if respstr['data'] == 'SUCCESS':
            logger.info('monthly send email success')
            return 'success'
        flag += 1
        logger.info('monthly send email fail')
        return 'fail'

    else:
        logger.info('monthly send email fail')
        return 'fail'

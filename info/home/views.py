from . import home_blue
import mongodb
from info.utils.common import get_last_month_date
from info.result import SUCCESS
from flask import request
import time


@home_blue.route('/home', methods=['GET', 'POST'])
def get_index_info():
    """
    首页各种数据信息统计展示
    :return:
    """
    # 同步月报统计的表格信息展示，展示的数据主要包括，A代表apilog类型，B代表nginx-access类型。
    # [项目名称，代号，告警总数，A/B告警数，A/B完成数，A/B未完成数，A/B完成率，总完成率。]
    select_month = request.json.get('selectMonth')
    if select_month:
        mon_start_date = select_month + '.01'
        mon_end_date = select_month + '.31'
    else:    # 首页默认可是当前月份，不默认统计之前月份信息。
        # mon_start_date, mon_end_date = get_last_month_date()
        tm_year = time.localtime().tm_year  # 当前年份
        tm_mon = time.localtime().tm_mon  # 当前月份
        if tm_mon <= 10:
            tm_mon = '0' + str(tm_mon)
        mon_start_date = str(tm_year) + '.' + str(tm_mon) + '.01'
        mon_end_date = str(tm_year) + '.' + str(tm_mon) + '.31'
    tm_year = mon_start_date.split('.')[0]
    tm_mon = mon_start_date.split('.')[1]
    content = '{}年{}月份日志告警信息统计结果如下:\n\n'.format(tm_year, tm_mon)
    project_list = list(mongodb.PROJECT.find())
    data = []
        # {"项目名称", "项目代号", "告警总数", "A/N告警数", "A/N完成数", "A/N未完成数", "A/N完成率", "总完成率"}

    for project in project_list:
        project_name = project.get('name')   # 项目名称
        project_app = project.get('app')     # 项目代号
        log_info_total_num = mongodb.LOGINFO.find({'app': project_app, 'update_time': {'$gte': mon_start_date, '$lte': mon_end_date}}).count()
        api_log_num = mongodb.LOGINFO.find({'app': project_app, 'type': 'apilog',
                                            'update_time': {'$gte': mon_start_date,
                                                            '$lte': mon_end_date}}).count()
        nginx_access_num = mongodb.LOGINFO.find({'app': project_app, 'type': 'nginx-access',
                                                 'update_time': {'$gte': mon_start_date,
                                                                 '$lte': mon_end_date}}).count()
        api_log_solve_num = mongodb.LOGINFO.find({'app': project_app, 'type': 'apilog', 'status': {'$in': [2, 3]},
                                                  'update_time': {'$gte': mon_start_date,
                                                                  '$lte': mon_end_date}}).count()
        nginx_access_solve_num = mongodb.LOGINFO.find({'app': project_app, 'type': 'nginx-access', 'status': {'$in': [2, 3]},
             'update_time': {'$gte': mon_start_date, '$lte': mon_end_date}}).count()
        api_log_not_solve_num = api_log_num - api_log_solve_num
        nginx_access_not_solve_num = nginx_access_num - nginx_access_solve_num
        if api_log_num:
            api_log_solve_percentage = '%.2f%%' % ((api_log_solve_num / api_log_num) * 100)
        else:
            api_log_solve_percentage = '100%'
        if nginx_access_num:
            nginx_access_solve_percentage = '%.2f%%' % ((nginx_access_solve_num / nginx_access_num) * 100)
        else:
            nginx_access_solve_percentage = '100%'
        log_info_total_solve_num = mongodb.LOGINFO.find({'app': project_app, 'status': {'$in': [2, 3]},
                                                             'update_time': {'$gte': mon_start_date,
                                                                             '$lte': mon_end_date}}).count()
        if log_info_total_num:
            log_info_total_solve_percentage = '%.2f%%' % ((log_info_total_solve_num / log_info_total_num) * 100)
        else:
            log_info_total_solve_percentage = '100%'
        project_data = {
            "name": project_name, "app": project_app, "total_num": log_info_total_num,
            "A/N_total_num": "{}/{}".format(api_log_num, nginx_access_num),
            "A/N_solve_num": "{}/{}".format(api_log_solve_num, nginx_access_solve_num),
            "A/N_not_solve_num": "{}/{}".format(api_log_not_solve_num, nginx_access_not_solve_num),
            "A/N_solve_num_per": "{}/{}".format(api_log_solve_percentage, nginx_access_solve_percentage),
            "total_per": log_info_total_solve_percentage
        }
        data.append(project_data)
    result = {
        "data": data,
        "title": '{}年{}月份日志告警信息统计结果如下:'.format(tm_year, tm_mon)

    }
    return SUCCESS(data=result)

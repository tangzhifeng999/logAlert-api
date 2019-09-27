from . import count_blue
import mongodb
from flask import request
from bson.objectid import ObjectId
from info.result import ERROR, SUCCESS
import datetime

"""
修改任务状态很开启关闭和轮询任务为同一个接口
"""
@count_blue.route('/create/count', methods=['POST'])
def create_count():
    """
    新建周期统计任务
    :return:
    """
    app = request.json.get('app')
    name = request.json.get('name')
    type = request.json.get('type')
    interval = int(request.json.get('interval'))  # 这个周期对应的是日：1，周：7，月30，其他：0，对应的count_tasks_num。
    params = request.json.get('params')
    crontab = request.json.get('crontab')
    person = request.json.get('person')
    time_range = request.json.get('time_range')    # ['', '']   # 绑定type=3
    if not isinstance(params, list):
        return ERROR(errno=201, errmsg='参数类型错误')
    if type == 2:
        a = mongodb.TASK.find_one({'type': type, 'app': app, 'name': name, 'interval': interval})
    else:
        a = mongodb.TASK.find_one({'type': type, 'app': app, 'name': name, 'time_range': time_range})
    if a:
        return ERROR(errno=201, errmsg='统计任务已经存在')
    filters = {}
    now = datetime.datetime.now()
    if app and name and params and type:
        filters.update({'app': app, 'name': name, 'params': params, 'person': person,  'status': 0, 'createAt': now,
                                                                    'type': type,
                                                                    'createAtStr': now.strftime('%Y-%m-%d %H:%M:%S'),
                                                                    'dateStr': now.strftime('%Y-%m-%d')})
    if crontab:
        filters.update({'crontab': crontab, 'interval': interval, 'status': 0, 'pid': ''})
    if time_range:
        filters.update({'time_range': time_range, 'status': 0, 'pid': ''})
    mongodb.TASK.insert_one(filters)
    mongodb.PROJECT.find_one_and_update({'app': app}, {"$inc": {"count_tasks_num": 1}})
    return SUCCESS()


@count_blue.route('/modify/count', methods=['POST'])
def modify_count():
    """
    修改周期统计任务
    :return:
    """
    oid = request.json.get('id')
    app = request.json.get('app')
    name = request.json.get('name')
    person = request.json.get('person')
    type = request.json.get('type')
    now = datetime.datetime.now()
    interval = request.json.get('interval')  # 这个周期对应的是日：1，周：7，月30，其他：0，对应的count_tasks_num。
    params = request.json.get('params')
    crontab = request.json.get('crontab')
    time_range = request.json.get('time_range')    # ['', '']
    if crontab:
        mongodb.TASK.find_one_and_update({'_id': ObjectId(oid)}, {'$set': {'params': params, 'type': type, 'person':person,
                                                                               'crontab': crontab, 'interval': interval,
                                                                               'createAtStr': now.strftime(
                                                                                   '%Y-%m-%d %H:%M:%S'),
                                                                               'dateStr': now.strftime('%Y-%m-%d')}})
    else:
        mongodb.TASK.find_one_and_update({'_id': ObjectId(oid)}, {'$set': {'params': params, 'type': type,
                                                                           'time_range': time_range, 'person': person,
                                                                           'createAtStr': now.strftime(
                                                                               '%Y-%m-%d %H:%M:%S'),
                                                                           'dateStr': now.strftime('%Y-%m-%d')}})
    return SUCCESS()
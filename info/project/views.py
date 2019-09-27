import os
import signal
import logging
from . import project_blue
import mongodb
from flask import request
from bson.objectid import ObjectId
from info.result import ERROR, SUCCESS
import datetime


logger = logging.getLogger('myapp')


@project_blue.route('/person/list', methods=['GET'])
def get_person_list():
    """
    获取项目接收人信息
    :return:
    """
    person_list = mongodb.USER.distinct('name')   # distinct的是去重，返回结果形式为list。
    return SUCCESS(data=person_list)


@project_blue.route('/create/project', methods=['POST'])
def create_project():
    """
    新建项目
    tasks_num：轮训任务数
    count_tasks_num： 统计任务数
    :return:
    """
    app = request.json.get("app")   # 项目在elk中配置的项目代号
    name = request.json.get('name')     # 项目的中文名，我们对项目的称呼
    if not all([app, name]):        # python all()函数，用来判断可迭代对象的内部参数是否都为true，但是可迭代对象为空的结果也为true。
        return ERROR(errno=201, errmsg='参数缺失')
    result1 = mongodb.PROJECT.find_one({"app": app})
    if result1:
        return ERROR(errno=201,errmsg='项目代号已经存在')
    result2 = mongodb.PROJECT.find_one({'name': name})
    if result2:
        return ERROR(errno=201, errmsg='项目名称已经存在')
    insert = mongodb.PROJECT.insert_one({'app': app, "name": name, 'tasks_num': 0, 'count_tasks_num': 0})
    if insert:
        return SUCCESS(data='新建项目成功')
    return ERROR(errno=201, errmsg='新建项目失败')


@project_blue.route('/modify/project', methods=["POST"])
def modify_project():
    """
    修改项目信息
    :return:
    """
    id = request.json.get('id')
    app = request.json.get("app")
    name = request.json.get('name')
    if not all([id, app, name]):
        return ERROR(errno=201, errmsg='参数缺失')
    old_project = mongodb.PROJECT.find_one({'_id': ObjectId(id)})
    old_app = old_project.get('app')
    old_name = old_project.get('name')
    if old_app != app or old_name != name:
        # mongo中find_One_and_update 找到并修改成功会返回修改的文档，否则会返回None
        update_id = mongodb.PROJECT.find_one_and_update({"_id": ObjectId(id)}, {'$set': {'app': app, "name": name}})
        if not update_id:
            return ERROR(errno=201, errmsg="修改项目信息失败")
        # 修改项目信息需要针对项目app的修改去改正任务中关联的项目
        mongodb.TASK.update({'app': old_app}, {'$set': {'app': app, 'name': name}}, upsert=False, multi=True)
        mongodb.LOGINFO.update({'app': old_app}, {'$set': {'app': app, 'name': name}}, upsert=False, multi=True)
    return SUCCESS()


@project_blue.route('/project/list', methods=['POST'])
def get_project_list():
    """获取项目列表"""
    keyword = request.json.get('keyword', '')
    page = request.json.get('page', 1)
    per_page = request.json.get('per_page', 8)
    skip = per_page * (page - 1)
    limit = per_page
    filters = {}
    if keyword:
        #  regex 是mongo中的模糊查询，支持字符串形式的值。
        filters.update({'$or': [{'app': {'$regex': keyword}}, {'name': {'$regex': keyword}}]})
    total_count = mongodb.PROJECT.find(filters).count()
    data_list = list(mongodb.PROJECT.find(filters).skip(skip).limit(limit))
    result = {
        'data': data_list,
        "count": total_count
    }
    return SUCCESS(data=result)


@project_blue.route('/project/detail', methods=['POST'])
def get_project_detail():
    """
    项目管理查看详情
    :return:
    """
    id = request.json.get('id')
    if not id:
        return ERROR(errno=201, errmsg='参数缺失')
    project = mongodb.PROJECT.find_one({'_id': ObjectId(id)})
    app = project.get('app')
    find_result = mongodb.TASK.find({'app': app}).sort([('type', 1), ('status', -1), ('createAtStr', -1)])
    if not find_result:
        return ERROR(errno=201, errmsg='项目信息查询失败')
    data = {
        'project': project,
        'task': find_result
    }
    return SUCCESS(data=data)


@project_blue.route('/modify/tasks/status', methods=["POST"])
def modify_tasks_status():
    """
    修改任务状态信息, status参数说明，0代表停止，1代表开始。
    :return:
    """
    oid = request.json.get("id")
    status = int(request.json.get("status"))
    if oid is None or status is None:
        return ERROR(errno=201, errmsg="参数缺失")
    task = mongodb.TASK.find_one({'_id': ObjectId(oid)})
    pid = task.get('pid')
    if pid:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception as e:
            logger.warning('pid kill failed : {}, error message id {}'.format(pid, e))
    mongodb.TASK.find_one_and_update({'_id': ObjectId(oid)}, {'$set': {'status': status, 'pid': ''}})
    return SUCCESS()


@project_blue.route('/create/task', methods=['POST'])
def create_task():
    """
    新建任务（周期性轮询任务）
    :return:
    """
    app = request.json.get('app')
    name = request.json.get('name')
    timeCell = int(request.json.get('timeCell'))    # timeCell 轮训时间执行的时间间隔，单位是minute
    times = int(request.json.get('times'))          # times   触发告警的次数
    params = request.json.get('params').strip()       # 轮训查询参数
    way = request.json.get('way')                   # 告警通知方式，主要是sms对应短信，email对应邮箱
    person = request.json.get('person')
    if not all([app, name, timeCell, times, params, way, person]):
        return ERROR(errno=201, errmsg='参数缺失')
    now = datetime.datetime.now()
    insert_data = {
        "app": app,
        "name": name,
        'timeCell': timeCell,
        'times': times,
        'params': params,
        'way': way,
        'person': person,
        "pid": '',
        'type': 1,    # 用type来区分任务分类，1为正常的轮询任务，2为周期统计任务，3为执行一次的统计任务。
        'createAt': now,
        'createAtStr': now.strftime('%Y-%m-%d %H:%M:%S'),
        'dateStr': now.strftime('%Y-%m-%d')
    }
    find_data = {
        "app": app,
        "name": name,
        'timeCell': timeCell,
        'times': times,
        'params': params,
    }
    result_id = mongodb.TASK.find_one(find_data)
    if result_id:
        return ERROR(errmsg="任务已经存在", errno=201)
    insert_data.update({"status": 0})   # 默认创建任务的时候，初始为停止状态。
    insert_id = mongodb.TASK.insert_one(insert_data)
    if not insert_id:
        return ERROR(errno=201, errmsg='新建任务失败')
    else:
        update = mongodb.PROJECT.find_one_and_update({'app': app}, {"$inc": {"tasks_num": 1}})
        if not update:
            return ERROR(errmsg='任务数更新失败', errno=201)
    return SUCCESS(data='新建任务成功')


@project_blue.route('/modify/task/info', methods=['POST'])
def modify_task():
    """
    修改任务
    :return:
    """
    oid = request.json.get('id')
    app = request.json.get('app')
    name = request.json.get('name')
    timeCell = int(request.json.get('timeCell'))
    times = int(request.json.get('times'))
    params = request.json.get('params').strip()
    way = request.json.get('way')
    person = request.json.get('person')
    if not all([oid, app, name, timeCell, times, params, way, person]):
        return ERROR(errno=201, errmsg='参数缺失')
    now = datetime.datetime.now()
    find_data = {
        "app": app,
        "name": name,
        'timeCell': timeCell,
        'times': times,
        'params': params,
        'way': way,
        'person': person
    }
    find = mongodb.TASK.find_one(find_data)
    if find:
        return ERROR(errno=201, errmsg='任务信息已经存在')
    insert_data = {
        "app": app,
        "name": name,
        'timeCell': timeCell,
        'times': times,
        'params': params,
        'way': way,
        'person': person,
        'createAt': now,
        'createAtStr': now.strftime('%Y-%m-%d %H:%M:%S'),
        'dateStr': now.strftime('%Y-%m-%d')
    }
    insert_data.update({"status": 0, 'pid': ''})  # 修改时候其实就是任务停止状态，这个可以有可以无。添加保证一下。
    mongodb.TASK.find_one_and_update({'_id': ObjectId(oid)}, {'$set': insert_data})
    return SUCCESS(data='修改任务成功')


@project_blue.route('/delete/task', methods=["POST"])
def delete_task():
    """
    删除任务,type参数说明，1代表轮训任务，2为统计任务，3为单次执行的统计任务。删除任务可以适应不同类型的任务
    :return:
    """
    oid = request.json.get('id')
    app = request.json.get('app')
    if not all([oid, app]):
        return ERROR(errno=201, errmsg='参数缺失')
    task = mongodb.TASK.find_one({'_id': ObjectId(oid)})
    task_type = task.get('type')
    delete = mongodb.TASK.delete_one({'_id': ObjectId(oid)})
    if not delete:
        return ERROR(errmsg='删除任务失败', errno=201)
    #  mongo的 $inc方法可以对一个值进行数学运算
    if task_type == 1:
        mongodb.PROJECT.find_one_and_update({'app': app}, {"$inc": {"tasks_num": -1}})
    elif task_type == 2:
        mongodb.PROJECT.find_one_and_update({'app': app}, {"$inc": {"count_tasks_num": -1}})
        # 删除统计任务，需要做记录，要是该项目的统计任务数量为0，那么就自动关闭这个项目的统计。
    return SUCCESS()



from info.controller import log_blue
from flask import request, session
import mongodb
from bson.objectid import ObjectId  # python中用来处理ObjectId的。str--->ObjectId
import datetime
from info.result import SUCCESS, ERROR


@log_blue.route('/app/list', methods=['GET'])
def get_app_list():
    """
    获取所有的项目列表
    :return:
    """
    app_list = mongodb.PROJECT.distinct('name')
    return SUCCESS(data=app_list)


@log_blue.route('/logInfo/list', methods=['POST'])
def get_loginfo_list():
    """
    获取告警日志信息列表
    {
        msgMD5:{
            'message':[timestamp,tiestamp]
        },
        app:hotel,
        type:apilog,
        time:now ==>这个字段是保证能够在轮询任务人为或者是宕机是，根据判断状态重新启动轮询
    }
    :return:
    """
    name = request.json.get('name')
    status = request.json.get('status')
    report_time = request.json.get('report_time')
    keywords = request.json.get('keywords')
    page = request.json.get('page', 1)
    per_page = request.json.get('per_page', 8)
    skip = per_page * (page - 1)
    limit = per_page
    filters = {}
    if name:
        filters.update({"name": name})
    if status != '':
        filters.update({"status": status})
    if report_time:
        if type(report_time) != list:
            return ERROR(errno=201, errmsg='时间范围格式错误')
        begin_str, end_str = report_time
        filters.update({"update_time": {
            '$gte': begin_str,
            '$lte': end_str}
        })
    if keywords:
        keywords.strip()
        filters.update({'loginfo.message': {'$regex': keywords}})
    total_count = mongodb.LOGINFO.find(filters).count()
    loginfo_list = list(mongodb.LOGINFO.find(filters).sort([('time', -1)]).skip(skip).limit(limit))
    result = {
        "count": total_count,
        "data": loginfo_list
    }
    return SUCCESS(data=result)


@log_blue.route('/logInfo/detail', methods=['POST'])
def get_loginfo_detail():
    """
    获取日志告警信息详情
    :return:
    """
    oid = request.json.get('id')
    per_page = request.json.get('per_page')
    page = request.json.get('page')
    if not all([oid, per_page, page]):
        return ERROR(errno=201, errmsg='参数缺失')
    result = mongodb.LOGINFO.find_one({"_id": ObjectId(oid)})
    timeline = result['loginfo']['timeline']
    total_num = len(timeline)
    timeline.sort(reverse=True)
    start_index = (page - 1) * page
    end_index = page * per_page
    timeline = timeline[start_index: end_index]
    result['timeline'] = timeline
    result['total_num'] = total_num
    if not result:
        return ERROR(errno=201, errmsg="查询失败")
    return SUCCESS(data=result)


@log_blue.route('/logInfo/check', methods=['POST'])
def loginfo_check():
    """
    确认日志告警问题,当出发报警条件，会在这个文档中存在一个字段，status，初始值为0，然后确认问题之后，"status"set为1。
    :return:
    """
    oid = request.json.get('id')
    note = request.json.get('note')
    if not oid:
        return ERROR(errno=201, errmsg='参数缺失')
    log_info = mongodb.LOGINFO.find_one({'_id': ObjectId(oid)})
    if not log_info:
        return ERROR(errno=201, errmsg='待确认的日志信息不存在')
    update_result = mongodb.LOGINFO.update({'_id': ObjectId(oid), 'status': 0},
                                          {'$set': {'status': 1}})
    if not update_result:
        return ERROR(errno=201, errmsg='待确认操作失败')
    # 生成处理记录信息
    name = session.get('username')
    time_str = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
    params = {
        'info_id': ObjectId(oid), 'name': name, 'tag': name + '确认问题', 'time': time_str, 'note': note
    }
    insert_id = mongodb.HANDLERECORD.insert_one(params)
    if not insert_id:
        return ERROR(errno=201, errmsg='确认日志信息记录失败')
    return SUCCESS(data='日志信息确认成功')


@log_blue.route('/logInfo/solve', methods=['POST'])
def log_info_solve():
    """
    解决日志问题，当用户点击对应的已解决按钮，改变对应的文档字段status，1变为2。
    :return:
    """
    oid = request.json.get('id')
    note = request.json.get('note')
    if not oid:
        return ERROR(errno=201, errmsg='参数缺失')
    loginfo = mongodb.LOGINFO.find_one({'_id': ObjectId(oid)})
    if not loginfo:
        return ERROR(errno=201, errmsg='待确认的日志信息不存在')
    updateresult = mongodb.LOGINFO.update({'_id': ObjectId(oid), 'status': 1},
                                          {'$set': {'status': 2}})
    if not updateresult:
        return ERROR(errno=201, errmsg='日志问题解决失败')
    name = session.get('username')
    time_str = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
    params = {
        'info_id': ObjectId(oid), 'name': name, 'tag': name + '解决问题', 'time': time_str, 'note': note
    }
    insert_id = mongodb.HANDLERECORD.insert_one(params)
    if not insert_id:
        return ERROR(errno=201, errmsg='解决日志信息记录失败')
    return SUCCESS(data='日志问题成功解决')


@log_blue.route('/logInfo/close', methods=['POST'])
def log_info_close():
    """
    关闭日志问题，迭代后为不再告警，项目相关人认为该日志问题不存在问题隐患，或者是该日志问题为正常写入的日志信息，
    可以选择直接关闭问题，status状态设置为3，再次出现后不会触发告警。
    同时，日志相关负责人认为不存在安全隐患可以直接关闭。
    :return:
    """
    oid = request.json.get('id')
    note = request.json.get('note')
    if not all([oid, note]):
        return ERROR(errno=201, errmsg='参数缺失')
    log_info = mongodb.LOGINFO.find_one({'_id': ObjectId(oid)})
    if not log_info:
        return ERROR(errno=201, errmsg='设置的日志信息不存在')
    # 修改对应日志文件的状态，status：0---->1
    update_result = mongodb.LOGINFO.update_one({'_id': ObjectId(oid)},
                                          {'$set': {'status': 3}})
    if not update_result:
        return ERROR(errno=201, errmsg='不再告警设置失败')
    name = session.get('username')
    time_str = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
    params = {
        'info_id': ObjectId(oid), 'name': name, 'tag': name + '设置该条日志为不再告警', 'time': time_str, 'note': note
    }
    insert_id = mongodb.HANDLERECORD.insert_one(params)
    if not insert_id:
        return ERROR(errno=201, errmsg='设置不再告警日志信息记录失败')
    return SUCCESS(data='不再告警设置成功')


@log_blue.route('/logInfo/resume', methods=['POST'])
def log_info_resume():
    """
    日志恢复告警，为了避免设置为不再告警的日志无法重新监控到，提供了一个恢复告警的状态，该条日志重新恢复到已完成状态，再次捕获的为正常状态。
    :return:
    """
    oid = request.json.get('id')
    note = request.json.get('note')
    if not all([oid, note]):
        return ERROR(errno=201, errmsg='参数缺失')
    log_info = mongodb.LOGINFO.find_one({'_id': ObjectId(oid)})
    if not log_info:
        return ERROR(errno=201, errmsg='恢复告警的日志信息不存在')
    # 修改对应日志文件的状态，status：0---->1
    update_result = mongodb.LOGINFO.update_one({'_id': ObjectId(oid)},
                                          {'$set': {'status': 2}})
    if not update_result:
        return ERROR(errno=201, errmsg='恢复告警设置失败')
    name = session.get('username')
    time_str = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
    params = {
        'info_id': ObjectId(oid), 'name': name, 'tag': name + '恢复该条日志的告警监控', 'time': time_str, 'note': note
    }
    insert_id = mongodb.HANDLERECORD.insert_one(params)
    if not insert_id:
        return ERROR(errno=201, errmsg='恢复告警信息记录失败')
    return SUCCESS(data='恢复告警设置成功')


@log_blue.route('/handleRecord', methods=['POST'])
def get_handle_record_list():
    """
    获取日志处理记录详情
    :return:
    """
    id = request.json.get('id')
    if not id:
        return ERROR(errno=201, errmsg='参数缺失')
    result_list = list(mongodb.HANDLERECORD.find({'info_id': ObjectId(id)}).sort("time", -1))
    return SUCCESS(data=result_list)


@log_blue.route('/batch_not_alert', methods=['POST'])
def batch_not_alert():
    """
    批量处理告警消息，批量设置不再告警 ，不再告警的设置int为3。
    :return:
    """
    oids = request.json.get('ids')
    note = request.json.get('note')
    if not oids:
        return ERROR(errno=201, errmsg="请选择需要关闭的告警信息")
    for oid in oids:
        log_info = mongodb.LOGINFO.find_one({'_id': ObjectId(oid)})
        if not log_info:
            return ERROR(errno=201, errmsg='待设置的日志信息不存在')
        mongodb.LOGINFO.update_one({'_id': ObjectId(oid)}, {'$set': {'status': 3}})
        # 每一条告警消息对应添加相应的处理记录
        name = session.get('username')
        time_str = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        params = {
            'info_id': ObjectId(oid), 'name': name, 'tag': name + '将该条日志设置为不再告警', 'time': time_str, 'note': note
        }
        insert_id = mongodb.HANDLERECORD.insert_one(params)
        if not insert_id:
            return ERROR(errno=201, errmsg='解决日志信息记录失败')
    return SUCCESS(data='日志问题成功解决')


@log_blue.route('/batch_closure', methods=['POST'])
def batch_closure():
    """
    批量设置告警消息处理完成，处理完成的设置int为2。但是不能处理选中的设置为不再告警的日志消息。
    :return:
    """
    oids = request.json.get('ids')
    note = request.json.get('note')
    if not oids:
        return ERROR(errno=201, errmsg="请选择需要关闭的告警信息")
    for oid in oids:
        log_info = mongodb.LOGINFO.find_one({'_id': ObjectId(oid)})
        if not log_info:
            return ERROR(errno=201, errmsg='待设置的日志信息不存在')
        status = mongodb.LOGINFO.find_one({'_id': ObjectId(oid)}).get('status')
        if status == 3:
            continue
        mongodb.LOGINFO.update_one({'_id': ObjectId(oid)}, {'$set': {'status': 2}})
        # 每一条告警消息对应添加相应的处理记录
        name = session.get('username')
        time_str = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        params = {
            'info_id': ObjectId(oid), 'name': name, 'tag': name + '解决问题', 'time': time_str, 'note': note
        }
        insert_id = mongodb.HANDLERECORD.insert_one(params)
        if not insert_id:
            return ERROR(errno=201, errmsg='解决日志信息记录失败')
    return SUCCESS(data='日志问题成功解决')

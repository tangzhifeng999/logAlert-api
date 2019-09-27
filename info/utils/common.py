import datetime, re, hashlib, json, requests, os, mongodb, signal, time, random, logging
from apscheduler.schedulers.blocking import BlockingScheduler
from info.tasks.send_sms.tasks import send_message1
from info.tasks.send_email.tasks import send_email1, send_email2, send_email3
from bson.objectid import ObjectId
from pytz import timezone
from pymongo import MongoClient
from config import MONGO_URL
from apscheduler.triggers.cron import CronTrigger
from logConfig import logger

_tz = timezone('Asia/Shanghai')
mdb = MongoClient(MONGO_URL, connect=False)
db = mdb['logAlert']


def convert_params(params):
    """
    转化定义的查询规则，系统中规则参数为键值的形式，每个查询参数使用，分割，然后在这里解析，可以在match中通过match进行查找匹配。
    :param params:
    :return: filter
    """
    filter = []
    b = params.split(',')
    for c in b:
        d = c.split(':')
        match = {
            "match": {
                d[0]: d[1]
            }
        }
        filter.append(match)
    return filter


def get_yesterday_timestamp():
    """
    获取当前时间前一天的0点和24点的时间戳，根据这个可以对应日报
    注：这个查询是针对elk查询规则的参数，选择时间戳格式是最正确并且最有效的。
    :return:
    """
    # 今天日期
    today = datetime.date.today()
    # 昨天时间
    yesterday = today - datetime.timedelta(days=1)
    # 昨天开始时间戳
    yesterday_start_time = time.mktime(time.strptime(str(yesterday), '%Y-%m-%d')) * 1000
    # 昨天结束时间戳
    yesterday_end_time = (time.mktime(time.strptime(str(today), '%Y-%m-%d')) - 1) * 1000
    return yesterday_start_time, yesterday_end_time


def get_last_week_times():
    """
    获取当前时间的上一周的起始时间的时间戳，这个返回值可以对应周报。
    注：这个查询是针对elk查询规则的参数，选择时间戳格式是最正确并且最有效的。
    :return:
    """
    tm_wday = time.localtime().tm_wday
    today = datetime.date.today()     # 今天日期
    last_week_start_date = today - datetime.timedelta(days=tm_wday + 7)  # 上周的开始日期
    current_week_start_date = today - datetime.timedelta(days=tm_wday)  # 本周的开始日期
    # 上周开始时间戳
    last_week_start_time = time.mktime(time.strptime(str(last_week_start_date), '%Y-%m-%d')) * 1000
    # 昨天结束时间戳
    last_week_end_time = (time.mktime(time.strptime(str(current_week_start_date), '%Y-%m-%d')) - 1) * 1000
    return last_week_start_time, last_week_end_time


def get_last_month_times():
    """
    获取当前日期的上一个月的起始时间的时间戳，这个时间可以对应月报。
    注：这个查询是针对elk查询规则的参数，选择时间戳格式是最正确并且最有效的。
    :return:
    """
    tm_mday = time.localtime().tm_mday   # 当前月份的第几天
    tm_year = time.localtime().tm_year   # 当前年份
    tm_mon = time.localtime().tm_mon    # 当前月份
    today = datetime.date.today()  # 今天日期
    if tm_mon != 1:
        last_mon_start_date = str(tm_year) + '-' + str(tm_mon - 1) + '-' + '01'
    else:
        last_mon_start_date = str(tm_year - 1) + '-' + '12' + '-' + '01'
    current_mon_start_date = today - datetime.timedelta(days=tm_mday - 1)
    last_mon_start_time = (time.mktime(time.strptime(str(last_mon_start_date), '%Y-%m-%d'))) * 1000
    last_mon_end_time = (time.mktime(time.strptime(str(current_mon_start_date), '%Y-%m-%d')) - 1) * 1000
    return last_mon_start_time, last_mon_end_time


def get_last_month_date():
    """
    获取当前日期的上一个月的起始时间的日期字符串，这个时间可以对应月报统计当月信息。。
    :return:
    """
    tm_mday = time.localtime().tm_mday   # 当前月份的第几天
    tm_year = time.localtime().tm_year   # 当前年份
    tm_mon = time.localtime().tm_mon    # 当前月份
    today = datetime.date.today()  # 今天日期
    if tm_mon != 1:
        last_mon_start_date = str(tm_year) + '-' + str(tm_mon - 1) + '-' + '01'
    else:
        last_mon_start_date = str(tm_year) + '-' + '12' + '-' + '01'
    current_mon_start_date = today - datetime.timedelta(days=tm_mday - 1)
    last_mon_start_time = (time.mktime(time.strptime(str(last_mon_start_date), '%Y-%m-%d')))
    last_mon_end_time = (time.mktime(time.strptime(str(current_mon_start_date), '%Y-%m-%d')) - 1)
    last_mon_start_array = time.localtime(last_mon_start_time)
    last_mon_end_array = time.localtime(last_mon_end_time)
    last_mon_start_date = time.strftime("%Y.%m.%d", last_mon_start_array)
    last_mon_end_date = time.strftime("%Y.%m.%d", last_mon_end_array)
    return last_mon_start_date, last_mon_end_date


def msg_regex(msg):
    """
    对msg详细信息进行正则提取，排除干扰的数据内容，获取干净的日志错误信。干扰信息主要包括时间等因素。
    这个是为了排除掉告警消息中时间等信息参数的影响，让同一种错误能够很好的归类。
    :param msg:
    :return:
    """
    msg = re.sub(r'\[?\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d+\]? \[\S+\]', '', msg)
    msg = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '', msg)

    return msg


def msg_md5(msg):
    """
    对传入的message信息，进行加密，然后方便往mongo存储。由于错误信息error对应的太长，同时存储时键不能包含.
    :param msg:
    :return:
    """
    hash = hashlib.md5()
    hash.update(msg.encode())
    msg = hash.hexdigest()
    return msg


def timer(task_id):
    """
    mongo是线程安全的，然后进程传递会有警告.查询说是可以设置参数connect=Flase，但是好像没有啥卵用。
    定时函数。
    1.告警轮询任务：根据规则的需要能够根据指定分钟间隔执行某种逻辑功能。
    2.周期数据统计任务：根据设置配置的crontab规则，执行需要查询的规则。
        1.type=1,默认执行原本的轮训监控任务
    :return:
    """
    pid = os.getpid()
    logger.info('task run pid:{}'.format(pid))
    # 记录该任务的执行进程，并记录，然后control process就可以不走判断，pass，然后该进程下定时任务定期轮询。
    db.tasks.find_one_and_update({'_id': task_id}, {'$set': {'pid': pid}})
    task_config = db.tasks.find_one({'_id': task_id})     # 该进程中执行的轮询任务的相关配置信息,可以对一个ObjectId转ObjectId型
    type = task_config.get('type')
    # 如果type为1，触发的是周期告警轮询任务
    if type == 1:
        timeCell = task_config.get('timeCell')  # 轮询周期
        # logger.info('task timeCell:{}'.format(timeCell))
        sched = BlockingScheduler()
        sched.add_job(logAlert_update_info, 'interval', seconds=timeCell*60, args=(task_id,))
        logger.info('logAlert_update_info function will start,task_id is {}, timeCell is {}min'.format(task_id, timeCell))
        sched.start()
    #  周期统计类型，利用icon进行指定时间周期指执行统计,将项目里面配置的所有查询参数，查询汇总到邮件里直接发送。没有短信的选项了。
    elif type == 2:
        interval = task_config.get('interval')  # 按照不同的时间周期，有三种，日，周，月，需要根据这个判断查询的起始和结束时间
        crontab = task_config.get('crontab')
        logger.info(crontab)         # 按照crontab配置规则，决定统计的周期等参数
        sched = BlockingScheduler()
        sched.add_job(count_info_interval, CronTrigger.from_crontab(crontab), args=(task_id,))
        logger.info('count_info_interval will start and interval = {}，task_id is {}'.format(interval, task_id))
        sched.start()
    #    统计指定时间间隔的日志错误数量，不是轮询任务，运行一次获取到相关参数就结束统计
    elif type == 3:
        logger.info('count_info_once will start, task_id is {}'.format(task_id))
        count_once_info(task_id)


def initialize():
    """
    初始化函数，在项目每次启动都杀掉项目中已有的进程，然后重新根据任务状态重新启动。重启之后之前的进程会退出销毁。
    :return:
    """
    logger.info("start init function")
    task_list = list(mongodb.TASK.find())
    if len(task_list) == 0:
        return 'no tasks need init'
    for task in task_list:
        pid = task.get('pid')
        if pid:
            try:
                os.kill(pid, signal.SIGKILL)
                logger.info('initialize function kill pid:{} success'.format(pid))
            except Exception as e:
                logger.info('initialize function kill pid:{} failed'.format(pid))
                logger.info(e)
            mongodb.TASK.find_one_and_update({'_id': task['_id']}, {'$set': {'pid': ''}})
    logger.info("finish init")
    return 'initialize success'


def logAlert_update_info(task_id):
    logger.info('update info run task id -----{}'.format(task_id))
    task_config = db.tasks.find_one({'_id': ObjectId(task_id)})
    name = task_config.get('name')
    app = task_config.get('app')
    times = task_config.get('times')
    timeCell = task_config.get("timeCell")
    URL = 'http://test.yuxisoft.cn:19200/logstash-{}-*/doc/_search'.format(app)
    now = datetime.datetime.now()
    lastTime = now - datetime.timedelta(minutes=timeCell)
    start_time = lastTime.timestamp() * 1000
    end_time = now.timestamp() * 1000
    params = task_config.get('params')
    way = task_config.get('way')
    person = task_config.get('person')
    _range = {"range": {
        "@timestamp": {
            "gt": "{}".format(start_time),
            "lt": "{}".format(end_time)
        }
    }
    }
    filters = convert_params(params)
    filters.insert(0, _range)
    query_params = {
        "size": 1000,
        "sort": {
            "@timestamp": "desc"
        },
        "query": {
            "bool": {
                "filter": filters
            }
        }
    }

    logger.info('-------------')
    logger.info('query params:')
    logger.info('{}'.format(query_params))
    logger.info('-------------')

    headers = {
        'Content-Type': 'application/json'
    }
    query_params = json.dumps(query_params)
    result = requests.post(URL, headers=headers, data=query_params)
    resp_str = result.text
    resp_conn = json.loads(resp_str)

    logger.info('-------------')
    logger.info('query from elk result:')
    logger.info('{}'.format(resp_conn))
    logger.info('-------------')
    total = resp_conn['hits']['total']
    if total == 0:
        return
    # elk 每次返回结果都是限制1000条
    num = total // 1000 + 1
    for i in range(num):
        skip = i * 1000
        URL = 'http://test.yuxisoft.cn:19200/logstash-{}-*/doc/_search?size=1000&from={}'.format(app, skip)
        result = requests.post(URL, headers=headers, data=query_params)
        resp_str = result.text
        resp_conn = json.loads(resp_str)
        hits_list = resp_conn['hits']['hits']
        if hits_list != []:
            type_ = hits_list[0]['_source']['fields']['type']    # 类型主要就是两种，apilog，nginx-access
            path = hits_list[0]['_source']['source']           # 路径主要就是日志文件的路径
            # level只要就是针对不同的类型，错误相关的信息字段不是一个字段
            level = hits_list[0].get('_source').get('fields').get('level') if hits_list[0].get('_source').get(
                'fields').get('level') else hits_list[0].get('_source').get('http_status')
            # 指定一个专门存储不同日志信息的字典，用来判断是否可以触发告警，设计本意是在一次轮询中同一条日志触发告警的才存mongo。
            msg_dict = {}
            for hit in hits_list:
                timestamp = hit['_source']['@timestamp']
                message = hit.get('_source').get('message') if hit.get('_source').get('message') else hit.get(
                    '_source').get('uri')
                message = msg_regex(message)
                md5k = msg_md5(message)
                obj_ = dict(
                    message=message
                )
                msg_dict.setdefault(md5k, obj_).setdefault("timeline", []).append(timestamp)
            """msg_dict ==> {   md5k1:{"message":message, "timeline": [time1, time2]},
                                md5k2:{"message":message, "timeline": [time1, time2]}
                            }
            """
            # 判断条件，是否触发告警
            for msg in msg_dict.keys():
                # 判断该条告警日志是否被设置为不再告警状态。如果该条日志告警设置为不再告警，忽略！
                find_result = mongodb.LOGINFO.find_one({'loginfo.md5': msg, 'status': 3})
                if find_result:
                    continue
                if len(msg_dict[msg]['timeline']) >= times:
                    start_time_str = lastTime.strftime('%Y-%m-%d %H:%M:%S')
                    end_time_str = now.strftime('%Y-%m-%d %H:%M:%S')
                    email_message = msg_dict.get(msg).get('message')[:300]
                    if way == ['sms']:
                        logger.info('will send message')
                        result = send_message1(person, name, start_time_str, end_time_str, len(msg_dict[msg]['timeline']))
                        logger.info('send message result is {}'.format(result))
                    elif way == ['email']:
                        logger.info('will send email')
                        result = send_email1(person, name, params, start_time_str, end_time_str, len(msg_dict[msg]['timeline']), email_message)
                        logger.info('send email result is {}'.format(result))
                    else:
                        logger.info('will send message and email')
                        result1 = send_email1(person, name, params, start_time_str, end_time_str, len(msg_dict[msg]['timeline']), email_message)
                        result2 = send_message1(person, name, start_time_str, end_time_str, len(msg_dict[msg]['timeline']))
                        logger.info('send email result is {}'.format(result1))
                        logger.info('send message result is {}'.format(result2))
                    # 迭代的逻辑是要是日志的错误信息的md5相同，不会向数据库中添加一条记录，而是在原有的日志记录中的时间出现里添加一个。重启处理流程
                    log_exist = mongodb.LOGINFO.find_one({'app': app, 'loginfo.md5': msg})
                    if log_exist:
                        mongodb.LOGINFO.find_one_and_update({'app': app, 'loginfo.md5': msg},
                                                                        {'$set': {
                                                                            "update_time": now.strftime('%Y.%m.%d'),
                                                                            "time": now.strftime('%Y.%m.%d %H:%M:%S'),
                                                                            'status': 0
                                                                            },
                                                                        '$push': {
                                                                            'loginfo.timeline': {
                                                                                "$each": msg_dict.get(msg).get('timeline')
                                                                                }
                                                                            }
                                                                        })
                        _id = log_exist.get('_id')
                        mongodb.HANDLERECORD.insert_one({'info_id': _id, "name": "系统", "tag": "该日志问题再次出现，请及时解决",
                                                         "time": now.strftime('%Y-%m-%d %H:%M:%S')})
                    else:
                        insert_dict = {
                            'app': app,
                            "name": name,
                            'type': type_,
                            'path': path,
                            'level': level,
                            'status': 0
                        }
                        insert_dict.update({"loginfo": {"md5": msg, 'message': msg_dict.get(msg).get('message'),
                                            'timeline': msg_dict.get(msg).get('timeline'),
                                            }, "update_time": now.strftime('%Y.%m.%d'),    # update_time 根据筛选的时候使用。
                                            "time": now.strftime('%Y.%m.%d %H:%M:%S')    # 精确到时间可以根据告警邮件找到该条告警
                                            })
                        db.logInfo.insert(insert_dict)


def count_once_info(task_id):
    """
    针对设置的时间范围进行一次查询，执行一次之后即关闭，非周期执行任务
    :param task_id:
    :return:
    """
    logger.info('count once info task id :{} start'.format(task_id))
    task_config = db.tasks.find_one({'_id': ObjectId(task_id)})
    name = task_config.get('name')
    app = task_config.get('app')
    # pid = task_config.get('pid')
    time_range = task_config.get('time_range')
    start_time_str, end_time_str = time_range
    # start_time_str = task_config.get('start_time')
    # end_time_str = task_config.get('end_time')
    start_time = datetime.datetime.strptime(start_time_str, '%Y-%m-%d').timestamp() * 1000
    end_time_date = datetime.datetime.strptime(start_time_str, "%Y-%m-%d") + datetime.timedelta(days=1)
    end_time_date = datetime.datetime.strftime(end_time_date, '%Y-%m-%d')
    end_time= (time.mktime(time.strptime(end_time_date, '%Y-%m-%d')) - 1) * 1000
    URL = 'http://test.yuxisoft.cn:19200/logstash-{}-*/doc/_search'.format(app)
    params = task_config.get('params')
    # way = task_config.get('way')
    person = task_config.get('person')
    _range = {"range": {
        "@timestamp": {
            "gt": "{}".format(start_time),
            "lt": "{}".format(end_time)
        }
    }
    }
    content = ''
    for params in params:
        filters = convert_params(params)
        filters.insert(0, _range)
        query_params = {
            "sort": {
                "@timestamp": "desc"
            },
            "query": {
                "bool": {
                    "filter": filters
                }
            }
        }

        logger.info('-------------')
        logger.info('query params:')
        logger.info('{}'.format(query_params))
        logger.info('-------------')

        headers = {
            'Content-Type': 'application/json'
        }
        query_params = json.dumps(query_params)
        result = requests.post(URL, headers=headers, data=query_params)
        resp_str = result.text
        resp_conn = json.loads(resp_str)
        logger.info('-------------')
        logger.info('query from elk result:')
        logger.info('{}'.format(resp_conn))
        logger.info('-------------')
        total = resp_conn['hits']['total']
        content = content + "查询规则：{}， 出现次数：{} 次.\n".format(params, total)
    # 一次执行结束后将任务状态关闭，重复执行没有意义,只要临时需要这个数据做个统计
    db.tasks.find_one_and_update({'_id': ObjectId(task_id)}, {'$set': {'status': 0, 'pid': ''}})
    logger.info('project is {},count info once will send email'.format(app))
    logger.info('count once info will send email')
    start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time / 1000))
    end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time / 1000))
    result = send_email2(person, name, content, start_time_str, end_time_str)
    logger.info('count once info send email result is {}'.format(result))


def count_info_interval(task_id):
    """
    针对设置的参数定时统计数据，然后可以系统内可以控制添加和移除查询参数，也可以关闭项目的统计任务，不需要进行短信通知，只邮件发送。
    :param task_id:
    :return:
    """
    logger.info('count info interval task id is {}'.format(task_id))
    task_config = db.tasks.find_one({'_id': ObjectId(task_id)})
    name = task_config.get('name')
    app = task_config.get('app')
    interval = task_config.get('interval')
    if interval == 1:  # 当前日期前一天的起始和结束时间
        start_time, end_time = get_yesterday_timestamp()
    elif interval == 7:  # 当前日期的前一周的起始和结束时间
        start_time, end_time = get_last_week_times()
    else:    # 当前日期的前一个月的起始和结束时间
        start_time, end_time = get_last_month_times()
    URL = 'http://test.yuxisoft.cn:19200/logstash-{}-*/doc/_search'.format(app)
    person = task_config.get('person')
    params = task_config.get('params')
    # way = task_config.get('way')
    _range = {"range": {
        "@timestamp": {
            "gt": "{}".format(start_time),
            "lt": "{}".format(end_time)
        }
    }
    }
    # 统计任务，汇总同一个项目下的不同查询规则的参数，汇总所有查询结果，然后统一一个邮件发送。
    content = ''
    for params in params:
        filters = convert_params(params)
        filters.insert(0, _range)
        query_params = {
            "size": 1000,
            "sort": {
                "@timestamp": "desc"
            },
            "query": {
                "bool": {
                    "filter": filters
                }
            }
        }

        logging.info('-------------')
        logging.info('query params:')
        logging.info('{}'.format(query_params))
        logging.info('-------------')

        headers = {
            'Content-Type': 'application/json'
        }
        query_params = json.dumps(query_params)
        result = requests.post(URL, headers=headers, data=query_params)
        resp_str = result.text
        resp_conn = json.loads(resp_str)
        logging.info('-------------')
        logging.info('query from elk result:')
        logging.info('{}'.format(resp_conn))
        logging.info('-------------')
        total = resp_conn['hits']['total']
        content = content + "查询规则：{}， 出现次数：{} 次.\n".format(params, total)
    start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time/1000))
    end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time/1000))
    logger.info('project:{}count info interval will send email'.format(app))
    result = send_email3(person, name, content, start_time_str, end_time_str, interval)
    logger.info('count info interval send email result is {}'.format(result))

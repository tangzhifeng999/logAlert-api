from info.utils.common import timer
import mongodb
import os, signal
import multiprocessing
from logConfig import logger


def control_process():
    """
    定时根据数据库中任务的状态决定是否开启进程执行相关的轮训任务或者统计任务。
    :param :
    :return:
    """
    logger.info('start control_process to start process or not')
    try:
        tasks = list(mongodb.TASK.find({}))
    except Exception as e:
        logger.info('mongo find tasks failed, error message is {}'.format(e))
        tasks = []
    if tasks:
        logger.info('find tasks success')
        for task in tasks:
            logger.info('task control process info:---------------')
            logger.info('task_id--------{}'.format(task['_id']))
            logger.info('app-----{}'.format(task['app']))
            logger.info('params-----{}'.format(task['params']))
            logger.info('task status-----{}'.format(task['status']))
            logger.info('task pid-----{}'.format(task["pid"]))
            # 进程 异常停止态
            if task['status'] == 0 and task["pid"] != '':
                # 获取这个进程的ID，然后杀死,满足该条件证明该进程之前在监控
                pid = task['pid']
                try:
                    os.kill(pid, signal.SIGKILL)
                except Exception as e:
                    logger.info('kill pid:{} failed, error message is {}'.format(pid, e))
                    mongodb.TASK.find_one_and_update({'_id': task['_id']}, {'$set': {'pid': ''}})
            # 正常从停止态到运行态
            elif task['status'] == 1 and task["pid"] == '':
                logger.info('task is ready to get a pid and run')
                try:
                    task_id = task.get('_id')
                except Exception as e:
                    task_id = ''
                    logger.info('no task, maybe task is deleted')
                if task_id:
                    try:
                        p = multiprocessing.Process(target=timer, args=(task_id,))
                        p.start()
                    except Exception as e:
                        logger.info('task pid start failed')
        logger.info('control process finished')
        return 'OK'
    return 'no tasks'

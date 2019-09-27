import mongodb
import requests
import json
import logging
from config import EMAIL

logger = logging.getLogger("myapp")

DEV = ''  # 开发环境地址
PRO = ''  # 生产环境地址

"""
    邮件内容或者是短信内容需要自己根据需要定义即可
"""


def send_email1(person_list, app_name, params, start_time, end_time,  times, message):
    """
    发送邮箱通知相关责任人告警
    :return:
    """
    receiver = []
    for person in person_list:
        result = mongodb.USER.find_one({'name': person})
        receiver.append(result['email'])
    content = """
    项目 {} 告警:
    
    满足查询规则：{} 的错误信息在{} - {} 内出现 {} 次.
    请及时登陆运维告警系统查看并处理。
    如有需要可以登陆elk 查看详细信息。
    
    日志错误信息(url或traceback）:
    
    {}
    
    """.format(app_name, params, start_time, end_time, times, message)
    date_dict = {
        "title": "【{}】告警".format(app_name),
        "content": content,
        "receiver": receiver
    }
    # logger.info(json.dumps(date_dict))
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
            return 'success'
        flag += 1
        return 'fail'

    else:
        return 'fail'


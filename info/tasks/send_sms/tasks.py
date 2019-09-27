import json, requests, mongodb


MSG_SUBMAIL_URL = ""
MSG_SUBMAIL_APP_ID = ""
MSG_SUBMAIL_SIGNATURE = ""


def send_message1(person, app_name, start_time, end_time, times):
    """发送短信通知相关负责人告警"""
    content = '【xxx】您好,您负责的项目: {} 的错误日志信息达到告警条件：{}次，请及时登陆告警后台系统确认并处理相关信息'.format(app_name, times)
    person_list = person
    result = []
    for person in person_list:
        person = mongodb.USER.find_one({'name': person})
        if person:
            post_data = {
                'appid': MSG_SUBMAIL_APP_ID,
                'signature': MSG_SUBMAIL_SIGNATURE,
                'to': person['mobile'],
                'content': content,
            }
            resp = requests.post(MSG_SUBMAIL_URL, data=post_data)
            resp.encoding = 'utf-8'
            respstr = json.loads(resp.text)
            if respstr['status'] == 'success':
                result.append('success')
            else:
                result.append('fail')
    if 'fail' in result:
        return 'fail'
    else:
        return 'success'

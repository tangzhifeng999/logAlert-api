import json
import requests


MSG_SUBMAIL_URL = ""
MSG_SUBMAIL_APP_ID = ""
MSG_SUBMAIL_SIGNATURE = ""


def sendlogAlertMessage(phone):
    content = '【xxx】您好，您负责的项目告警系统通知您有待处理信息，请及时登陆告警后台系统处理。'
    return sendTextMessage(phone, content)


def sendTextMessage(phone, content):
    postData={
        'appid': MSG_SUBMAIL_APP_ID,
        'signature': MSG_SUBMAIL_SIGNATURE,
        'to': phone,
        'content': content
    }
    return subMailSend(MSG_SUBMAIL_URL, postData)


def subMailSend(url, postData):
    flag = 1
    while True and flag <= 2:
        resp = requests.post(url, data=postData)
        resp.encoding = 'utf-8'
        respstr = json.loads(resp.text)
        if respstr['status'] == 'success':
            return 'success'
        flag += 1
    return 'fail'


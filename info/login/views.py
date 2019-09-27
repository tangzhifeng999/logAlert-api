from info.login import login_blue
from flask import request, session
import mongodb
from info.result import ERROR, SUCCESS


@login_blue.route('/admin/login', methods=['POST'])
def login():
    """
     根据用户登录输入的邮箱名和验证码，验证正确登陆完成。默认用户的登录账号统一为公司邮箱，初始密码默认为admin123。
    :return:
    """
    email = request.json.get('email')
    password = request.json.get('password')
    if not ([email, password]):
        return ERROR(errno=201, errmsg='参数缺失')
    user = mongodb.USER.find_one({'email': email})
    if not user:
        return ERROR(errno=201, errmsg='该用户不存在')
    if not user.get('status'):
        return ERROR(errno=201, errmsg='用户被禁用')
    real_password = user.get('password')
    if password != real_password:
        return ERROR(errno=201, errmsg='密码错误')
    session['username'] = user['name']
    return SUCCESS(data='用户登录成功')


@login_blue.route('/admin/logout')
def logout():
    """
     用户退出功能
    :return:
    """
    session.pop('username', None)
    return SUCCESS(data='用户退出成功')







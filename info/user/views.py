from flask import request
from info.user import user_blue
import mongodb
from bson import ObjectId
from info.result import ERROR, SUCCESS


@user_blue.route('/create/user', methods=['POST'])
def create_user():
    """
    新增用户
    :return:
    """
    body = request.json
    name = request.json.get('name')
    mobile = request.json.get('mobile')  # 告警触发后短信通知这个手机号
    email = request.json.get('email')    # 告警触发后或者统计报告邮箱通知
    password = request.json.get('password')
    if not ([name, mobile, email, password]):
        return ERROR(errno=201, errmsg='新增用户信息不全')
    body.update({'status': True})
    insert_id = mongodb.USER.insert_one(body)    # mongo再插入成功会返回插入文档的ID，mongo在插入只会做一些基本校验，_id重复，以及文档大小。因此很统一插入非法数据
    if insert_id:
        return SUCCESS(data='新增用户成功')
    return ERROR(errno=201, errmsg='新增用户失败')


@user_blue.route('/user/list', methods=['POST'])
def get_user_list():
    """
    获取用户列表
    :return:
    """
    page = request.json.get('page', 1)     # dict.get(key, default=None)
    per_page = request.json.get('per_page', 8)
    skip = per_page * (page - 1)   # 跳过前多少数据，不建议skip太多数据，会导致速度变慢，但是获取下一页可以使用上一页的最后一个数据的结果来计算下一页的初始数据
    limit = per_page
    total_count = mongodb.USER.find().count()
    # mongo的find查询返回的是mongo的游标对象，不会立即查询数据库，在需要真的获取结果是才回查询数据库。可以通过curson.next()迭代后续结果
    user_list = list(mongodb.USER.find().sort('status', -1).skip(skip).limit(limit))   # MONGO排序1为升序，-1为降序
    if not user_list:
        return ERROR(errno=201, errmsg='用户信息列表为空')
    result = {
        "data": user_list,
        "count": total_count
    }
    return SUCCESS(data=result)


@user_blue.route('/modify/user', methods=['POST'])
def modify_user_info():
    """
    修改编辑用户信息
    :return:
    """
    id = request.json.get('id')
    name = request.json.get('name')
    mobile = request.json.get('mobile')
    email = request.json.get('email')
    password = request.json.get('password')
    if not ([id, name, mobile, email, password]):
        return ERROR(errno=201, errmsg='修改用户所填信息不全')
    update_id = mongodb.USER.find_one_and_update({'_id': ObjectId(id)}, {'$set': {'name': name, 'email': email, 'password': password,
                                                                       'mobile': mobile}})
    if update_id:
        return SUCCESS(data='用户信息修改成功')
    return ERROR(errno=201, errmsg='用户信息修改失败')


@user_blue.route('/change/user/status', methods=['POST'])
def change_user_status():
    """
    修改用户状态信息
    :return:
    """
    id = request.json.get('id')
    if not id:
        return ERROR(errno=201, errmsg='参数不全')
    user = mongodb.USER.find_one({'_id': ObjectId(id)})   # find_one会返回查询结果的布尔值，找到会true，没有则为false，但是find无论如何都会返回一个查询游标
    if not user:
        return ERROR(errno=201, errmsg='所选操作用不存在')
    status = user.get('status')
    # 之前为启用，设置为禁用；之前为禁用，设置为启用
    if status:
        update_id = mongodb.USER.find_one_and_update({'_id': ObjectId(id)}, {'$set': {'status': False}})
    else:
        update_id = mongodb.USER.find_one_and_update({'_id': ObjectId(id)}, {'$set': {'status': True}})
    if not update_id:
        return ERROR(errno=201, errmsg='用户状态修改失败')
    return SUCCESS(data='用户状态修改成功')





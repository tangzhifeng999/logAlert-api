from bson.json_util import dumps


"""
1. 不能直接使用jsonify的原因是，mongo的id不能正常解析，需要用bson.json_util 里的dump来序列化。
2. 返回值code瞎写就完事了。
"""


def SUCCESS(data="SUCCESS"):
    result = {
        "code": 200,
        "data": data
    }
    return dumps(result)


def ERROR(errno, errmsg):
    result = {
        "code": errno,
        "errorMessage": errmsg
    }
    return dumps(result)

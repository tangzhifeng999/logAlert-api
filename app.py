# -*- coding:utf-8 -*-
from info import create_app
from flask_cors import CORS
from config import ENV
from logConfig import logger


app = create_app(ENV)
# 配置跨域
CORS(app, supports_credentials=True)


@app.route('/')
def index():
    return 'hello logAlert'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)

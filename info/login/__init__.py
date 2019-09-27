from flask import Blueprint


login_blue = Blueprint('login_blue', __name__)


from . import views

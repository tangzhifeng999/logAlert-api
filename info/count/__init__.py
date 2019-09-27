from flask import Blueprint


count_blue = Blueprint('count_blue', __name__)


from .import views
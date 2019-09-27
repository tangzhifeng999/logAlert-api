from flask import Blueprint


home_blue = Blueprint('home_blue', __name__)


from . import views
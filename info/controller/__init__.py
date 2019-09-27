from flask import Blueprint

log_blue = Blueprint('log_blue', __name__)

from . import views

import os
from datetime import timedelta

class Config(object):
    SECRET_KEY = os.environ.get('JhX99#I*agCw') or 'you-will-never-guess'
    SALT = b"/OY(?rz_u0-S?vdK"
    ITEMS_PER_PAGE = 20
    REVIEWS_PER_PAGE = 12
    USERS_SEARCH_LIMIT = 20
    # SECRET_KEY
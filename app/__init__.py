from flask import Flask
from config import Config
from flask_bootstrap import Bootstrap
from datetime import timedelta
import sqlite3

app = Flask(__name__)
app.config.from_object(Config)
bootstrap = Bootstrap(app)

from app import routes, models, error


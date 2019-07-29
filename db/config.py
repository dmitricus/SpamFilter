import os
basedir = os.path.abspath(os.path.dirname(__file__))

# Кодировка
ENCODING = 'utf-8'

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
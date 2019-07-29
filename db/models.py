import datetime
import os
from sqlalchemy import Column, Integer, String, BOOLEAN, BIGINT, INT, TEXT, FLOAT, DATE, ForeignKey, DateTime, VARCHAR, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker


Base = declarative_base()

# заносим в БД спаммеров, чтобы облегчить жизнь почтовке
USERNAME = ""
PASSWORD = ""
HOST = ""
DATABASE = ""

class Training(Base):
    __tablename__ = 'training'
    index = Column(BIGINT, primary_key=True)
    word = Column(TEXT, unique=True)
    spam = Column(BIGINT)
    no_spam = Column(BIGINT)
    probability_of_spam = Column(FLOAT)
    probability_not_spam = Column(FLOAT)

    def __init__(self, word, spam, no_spam, probability_of_spam, probability_not_spam):
        self.word = word
        self.spam = spam
        self.no_spam = no_spam
        self.probability_of_spam = probability_of_spam
        self.probability_not_spam = probability_not_spam

class Mail(Base):
    __tablename__ = 'mail'
    index = Column(BIGINT, primary_key=True)
    text = Column(TEXT, unique=True)
    ip = Column(VARCHAR)
    mail_from = Column(VARCHAR)
    rcpt_to = Column(VARCHAR)
    spam_or_no_spam = Column(BOOLEAN)
    date = Column(DATE)

    def __init__(self, text, ip, mail_from, rcpt_to, spam_or_no_spam, date):
        self.text = text
        self.ip = ip
        self.mail_from = mail_from
        self.rcpt_to = rcpt_to
        self.spam_or_no_spam = spam_or_no_spam
        self.date = date

# путь до папки где лежит этот модуль
DB_FOLDER_PATH = os.path.dirname(os.path.abspath(__file__))

# путь до файла базы данных
DB_PATH = os.path.join(DB_FOLDER_PATH, 'app.db')
#создаем движок
engine = create_engine('sqlite:///{}'.format(DB_PATH), echo=False)

#engine = create_engine('mysql+mysqldb://{}:{}@{}/{}'.format(USERNAME, PASSWORD, HOST, DATABASE), pool_recycle=3600)

# Не забываем создать структуру базы данных
Base.metadata.create_all(engine)
# Создаем сессию для работы
Session = sessionmaker(bind=engine)
session = Session()
# Рекомендуется брать 1 сессию и передавать параметром куда нам надо
# session = session
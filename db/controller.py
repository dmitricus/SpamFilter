from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, and_, or_, not_
import hashlib, uuid
from .models import Training, Mail

# Кодировка
ENCODING = 'utf-8'

class Storage:
    """Серверное хранилище"""

    def __init__(self, session):
        """
        Запоминаем сессию, чтобы было удобно с ней работать
        :param session:
        """
        self.session = session

    def ip_exists(self, word):
        """Проверка, что ip уже есть"""
        result_training = self.session.query(Training).filter(Training.word == word).count() > 0
        return result_training

    ########## SELECT #########################
    def select_training(self):
        try:
            # Все ip
            q_training = self.session.query(Training).all()
            return q_training
        except SQLAlchemyError as ex:
            print("Ошибка: {0}".format(ex))
        finally:
            self.session.close()

    def select_mail(self, spam_or_no_spam=None, date=None):
        try:
            if date:
                # Выборка по date часу
                q_mail = self.session.query(Mail).filter(Mail.date == date).all()
                return q_mail
            elif not spam_or_no_spam is None:
                # Выборка по
                q_mail = self.session.query(Mail).filter(Mail.spam_or_no_spam == spam_or_no_spam).all()
                return q_mail
            else:
                # Все mail
                q_mail = self.session.query(Mail).all()
                return q_mail
        except SQLAlchemyError as ex:
            print("Ошибка: {0}".format(ex))
        finally:
            self.session.close()

    ########## INSERT #########################
    def insert_training(self, word, spam, no_spam, probability_of_spam, probability_not_spam):
        try:
            # Для сохранения объекта, нужно добавить его к имеющейся сессии
            training = Training(word, spam, no_spam, probability_of_spam, probability_not_spam)
            self.session.add(training)
        except SQLAlchemyError as ex:
            print("Ошибка: {0}".format(ex))
            self.session.rollback()
        else:
            self.session.commit()
        finally:
            self.session.close()

    def insert_mail(self, text, ip, mail_from, rcpt_to, spam_or_no_spam, date):
        try:
            # Для сохранения объекта, нужно добавить его к имеющейся сессии
            training = Mail(text, ip, mail_from, rcpt_to, spam_or_no_spam, date)
            self.session.add(training)
        except SQLAlchemyError as ex:
            print("Ошибка: {0}".format(ex))
            self.session.rollback()
        else:
            self.session.commit()
        finally:
            self.session.close()

    ########## UPDATE #########################
    def update_training(self, word, spam, no_spam, probability_of_spam, probability_not_spam):
        try:
            self.session.query(Training).filter(Training.index == id).\
                update(dict(word=word, spam=spam, no_spam=no_spam, probability_of_spam=probability_of_spam,
                            probability_not_spam=probability_not_spam), synchronize_session=False)
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            return {'error': 'error'}
        return True

    def update_mail(self, text, ip, mail_from, rcpt_to, spam_or_no_spam, date):
        try:
            self.session.query(Mail).filter(Mail.index == id).\
                update(dict(text=text, ip=ip, mail_from=mail_from, rcpt_to=rcpt_to,
                            spam_or_no_spam=spam_or_no_spam, date=date), synchronize_session=False)
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            return {'error': 'error'}
        return True


    """
    qry = DBSession.query(User).filter(
        and_(User.birthday <= '1988-01-17', User.birthday >= '1985-01-17'))
    # or same:
    qry = DBSession.query(User).filter(User.birthday <= '1988-01-17').\
            filter(User.birthday >= '1985-01-17')
    Also you can use between:
    
    qry = DBSession.query(User).filter(User.birthday.between('1985-01-17', '1988-01-17'))
    """
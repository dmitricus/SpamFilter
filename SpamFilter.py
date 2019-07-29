#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging, os, sys
import time
import datetime
import random
from queue import Queue, Empty, Full
from threading import Thread, Event, Timer
import signal
import re
import subprocess
from spam_analysis import spam_analysis_main
from parser_msg import read_email
from db.models import session, engine
from db.controller import Storage

storage = Storage(session)
d = datetime.datetime.now()
dn = d.strftime("%Y-%m-%d")

FOLDER_PATH = "d:\\CommuniGate Files\\"
FOLDER_PATH_SPAMFILTER = "d:\\CommuniGate Files\\SpamFilter\\"
FOLDER_PATH_LOG = "d:\\CommuniGate Files\\SpamFilter\\SpamFilterLog\\"

PATH_LOG = os.path.join(FOLDER_PATH_LOG, '{}.log'.format(dn))

logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG,
                    filename=PATH_LOG)

# количество потоков обслуживающих очередь
num_worker_threads = 2
version = "0.00010 Windows-x86_64 build 10-02-2019"
TIMEOUT = 5 # Таймаут ожидания команд от сервера в секундах
pid = os.getpid() # ID процесса

def block_firewall(ip):
    if not ip == None:
        try:
            # Блокируем IP спамера на межсетевом экране
            # netsh advfirewall firewall add rule name="Блокировка IP" dir=in interface=any action=block remoteip=119.63.196.1/32
            output = subprocess.check_output('netsh advfirewall firewall add rule name="Блокировка IP {} SPAM" '
                                             'dir=in interface=any action=block remoteip={}/32'.format(
                                              ip, ip), shell=True, stderr=subprocess.STDOUT)
            logging.info("Блокировка IP: {} - {}".format(ip, output.decode('cp866')))
        except subprocess.CalledProcessError as e:
            logging.critical("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode,
                                                                        e.output.decode('cp866')))
        except Exception as e:
            logging.critical("Непридвиденная ошибка", e)

class CommandObject:
    piv = 4  # programInterfaceVersion
    command_count = 0

    def __init__(self, piv, command_count):
        self.piv = piv
        self.command_count = command_count

def do_work(noun):
    """
    Функция иммитирующая полезную работу
    """
    #sleep_time = random.randint(0, 10)
    #time.sleep(sleep_time)
    #PATH = os.path.join(FOLDER_PATH, '{}'.format(noun[2]))
    #f = open(PATH, 'r')
    #for text in f:
    #    logging.debug("MAIL {}: {}".format(noun[2], text))



    # Случайные решения антиспама для тестирования
    result = random.choice(["OK", "ADDHEADER", "DISCARD", "REJECTED", "FAILURE"])

    return result

def worker():
    """
    Основной код здесь
    """
    while True:
        # Получаем задание из очереди
        item = q.get()
        do_work(item)
        # Сообщаем о выполненном задании
        q.task_done()

def intf(noun):
    print('{} INTF {}'.format(noun[0], cmd.piv))

    logging.info('Ответ программы: {} INTF {}'.format(noun[0], cmd.piv))

def ok(noun):
    print('{} OK'.format(noun[0]))

    logging.info('Ответ программы: {} OK'.format(noun[0]))

"""
X-Junk-Score:  92 [XXXX]
X-Cloudmark-Score:  92 [XXXX]
X-Alert: possible spam!
X-Color: red
Цифровое значение рейтинга	Штрих-код
0	        []
1-39	    [X]
40-80	    [XX]
81-90	    [XXX]
91-95	    [XXXX]
96-99	    [XXXXX]
100	        [XXXXXX]
"""
# Изменение заголовка письма
def hendler(noun, spam_count=100):
    spam_count = round(spam_count)
    if spam_count > 100:
        spam_count = 100
    print('{} ADDHEADER "X-Spam-Score: 100 [XXXXX]"'.format(noun[0]))
    logging.info('Ответ программы: {} ADDHEADER "X-Spam-Score: 100 [XXXXX]"'.format(noun[0]))


def quit(noun):
    print('* processed: {} requests. Quitting.'.format(cmd.command_count))
    print('{} OK'.format(noun[0]))

    logging.info('Ответ программы: * processed: {} requests. Quitting.'.format(cmd.command_count))
    logging.info('Ответ программы: {} OK'.format(noun[0]))

    time.sleep(4.0)
    os.kill(pid, signal.SIGINT)

# Если сообщение должно быть отвергнуто, то строка с ответом должна иметь следующий формат:
# seqNum ERROR report
def error(noun, report=""):
    print('{} ERROR "{}"'.format(noun[0], report))

    logging.critical('Ответ программы: {} ERROR {}'.format(noun[0], report))

# Если сообщение должно быть выкинуто, то строка с ответом должна иметь следующий формат:
# seqNum DISCARD
def discard(noun):
    print('{} DISCARD'.format(noun[0]))

    logging.info('Ответ программы: {} DISCARD'.format(noun[0]))


# Если обработка сообщения должна отложена (из-за лицензионных ограничений, например), то строка с ответом должна иметь следующий формат:
# seqNum REJECTED report
def reject(noun, report=""):
    print('{} REJECTED {}'.format(noun[0], report))

    logging.info('Ответ программы: {} REJECTED {}'.format(noun[0], report))

# Если программа получает запрос, который она не может обработать, то она должна возвращать ответ FAILURE:
# seqNum FAILURE
def failure(noun):
    print('{} FAILURE'.format(noun[0]))

    logging.info('Ответ программы: {} FAILURE'.format(noun[0]))

# Проверяем сообщение на спам
def file(noun):
    """
    Функция генерирующая данные для очереди
    """
    try:
        #result = q.put(noun)
        spam_count = 0
        # получим разобранное сообщение
        message = read_email(FOLDER_PATH + noun[2])
        email_from = re.findall(r'@\w+.\w+.\w+', message['from'])

        # Проверка есть ли сообщение в белом или черном списке
        bl_email = re.findall(r'@\w+.\w+.\w+', open(FOLDER_PATH_SPAMFILTER + 'blacklist').read())
        wl_email = re.findall(r'@\w+.\w+.\w+', open(FOLDER_PATH_SPAMFILTER + 'whitelist').read())

        if email_from[0] in bl_email:
            hendler(noun, 100)
            storage.insert_mail(message['subject'], message['text'], message['ip'],
                                message['from'], message['to'], True, True, d)
            # Перед блокировкой надо посчитать количестов спама с этого ip
            if storage.select_mail(ip=message['ip']) >= 10:
                block_firewall(message['ip'])
            logging.debug("Отправитель {} находится в черном списке".format(message['from']))
        elif email_from[0] in wl_email:
            ok(noun)
            storage.insert_mail(message['subject'], message['text'], message['ip'],
                                message['from'], message['to'], message['spam_or_no_spam'], False, d)
            logging.debug("Отправитель {} находится в белом списке".format(message['from']))
        else:
            span_or_no_spam, spam_count = spam_analysis_main(message["text"])
            if type(span_or_no_spam) == bool:
                if span_or_no_spam:
                    hendler(noun, spam_count)
                    storage.insert_mail(message['subject'], message['text'], message['ip'],
                                        message['from'], message['to'], True, True, d)
                    # Перед блокировкой надо посчитать количестов спама с этого ip
                    if storage.select_mail(ip=message['ip']) >= 10:
                        block_firewall(message['ip'])
                    logging.debug("Отправитель {} СПАМЕР".format(message['from']))
                else:
                    ok(noun)
                    storage.insert_mail(message['subject'], message['text'], message['ip'],
                                        message['from'], message['to'], message['spam_or_no_spam'], False, d)
                    logging.debug("Отправитель {} Не спамер".format(message['from']))
            else:
                error(noun[0], "ERROR: Отправителя {} не получилось проверить".format(message['from']))

    except Exception as e:
        error(noun[0], str(e))

    """
    if result == "OK":
        ok(noun)
    elif result == "ADDHEADER":
        hendler(noun)
    elif result == "DISCARD":
        discard(noun)
    elif result == "REJECTED":
        reject(noun, "Postpone processing!")
    elif result == "FAILURE":
        failure(noun)
    """

class TimeoutExpired(Exception):
    pass


class Input:
    _response = None  # internal use only

    @classmethod
    def timeout(cls, timeout):
        cls._response = None
        thread = Thread(target=cls.do_input, args=())
        thread.start()
        # wait for a response
        thread.join(timeout)
        # closing input after timeout
        if cls._response is None:
            try:
                # clear response from enter key
                cls._response = None
                raise TimeoutExpired
            except TimeoutExpired:
                print("* FAILURE TIMEOUT - unable to access directory Submitted")
                os.kill(pid, signal.SIGINT)
            finally:
                thread.join()
        return cls._response

    @classmethod
    def do_input(cls):
        cls._response = input()

# 1 QUIT\r\n
# 9 INTF 4\r\n
def get_input():
    try:
        #command = Input.timeout(TIMEOUT).replace("\\n", "").replace("\\r", "").split()
        command = input().replace("\\n", "").replace("\\r", "").split()
        #for line in sys.stdin:
        #    command = line.replace("\\n", "").replace("\\r", "").split()
        logging.debug("Команда от сервера: {}".format(' '.join(command)))
        if command:
            if len(command) >= 2:
                cmd.seqnum = command[0]
                verb_word = command[1]
                if verb_word in verb_dict:
                    verb = verb_dict[verb_word]
                else:
                    logging.debug("Неизвестная команда от сервера: {}".format(' '.join(command)))
                    return
                noun_word = ' '.join(command)
                verb(command)
    except Exception as e:
        logging.critical('{}'.format(e))

if __name__ == '__main__':
    print("* CGPSSpamFilter plugin version {} started".format(version))
    #sys.stdout.write("* CGPSSpamFilter plugin version {} started".format(version))
    logging.info("############################################## СТАРТ ##############################################")
    logging.info("Ответ программы: * CGPSSpamFilter plugin version {} started".format(version))
    cmd = CommandObject

    verb_dict = {
        "INTF": intf,
        "COMMAND": ok,
        "QUIT": quit,
        "FILE": file,
    }
    # Создаем FIFO очередь
    q = Queue()
    # Создаем и запускаем потоки, которые будут обслуживать очередь
    for i in range(num_worker_threads):
        t = Thread(target=worker)
        t.setDaemon(True)
        t.start()

    # Ставим блокировку до тех пор пока не будут выполнены все задания
    q.join()
    while True:
        get_input()


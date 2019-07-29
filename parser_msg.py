import logging, os, sys
import email
import re
import regex
import nltk
import pymorphy2
from email.utils import parseaddr, parsedate
import email.charset
from glob import glob, iglob
from email import message_from_binary_file, policy
import datetime
from yandex.Translater import Translater
from db.models import session, engine
from db.controller import Storage
from langdetect import detect, detect_langs
from string import ascii_letters
from bs4 import BeautifulSoup



storage = Storage(session)


dictionary = {
    '3': 'з',
    'm': 'т',
    '0': 'о',
    'u': 'и',
    'q': 'д',
    'g': 'д',
    'b': 'в',
    'a': 'а',
    'p': 'р',
    'y': 'у',
    'e': 'е',
    'k': 'к',
    'o': 'о',
    'c': 'с',
    'x': 'х',

}
d = datetime.datetime.now()
dn = d.strftime("%Y-%m-%d")

FOLDER_PATH_SPAMFILTER = "d:\\CommuniGate Files\\SpamFilter\\"
FOLDER_PATH_LOG = "d:\\CommuniGate Files\\SpamFilter\\SpamFilterLog\\"
PATH_LOG = os.path.join(FOLDER_PATH_LOG, '{}.log'.format(dn))

logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG,
                    filename=PATH_LOG)

basedir = os.path.abspath(os.path.dirname(__file__))

# Регулярное выражение для гиперссылок
urls = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
# probability score threshold
prob_thresh = 0.4
morph = pymorphy2.MorphAnalyzer()

def del_fio(text):
    try:
        fio = []
        for word in nltk.word_tokenize(text):
            for p in morph.parse(word):
                if 'Surn' in p.tag and p.score >= prob_thresh:
                    fio.append('{}'.format(word))
                elif 'Name' in p.tag and p.score >= prob_thresh:
                    fio.append('{}'.format(word))
                elif 'Patr' in p.tag and p.score >= prob_thresh:
                    fio.append('{}'.format(word))
        body = re.sub(' '.join(fio), '', text)
        return body
    except Exception as e:
        logging.critical('Ошибка в функции del_fio: {}'.format(e))

# Удаление HTML тегов
def cleanhtml(raw_html):
    try:
      cleanr = re.compile('<.*?>')
      cleantext = re.sub(cleanr, '', raw_html)
      return cleantext
    except Exception as e:
        logging.critical('Ошибка в parser_msg.py функции cleanhtml: {}'.format(e))

def translate(text):
    try:
        if not text == None:
            tr = Translater()
            tr.set_key(
                'trnsl.1.1.20190220T065744Z.0cec4e9917c787ea.7f6ae416a8eac8afd573ddc81fbdb71462e7d632')
            # Api key found on https://translate.yandex.com/developers/keys
            tr.set_text(text)
            if not tr.detect_lang() == 'ru':
                tr.set_from_lang(tr.detect_lang())
                tr.set_to_lang('ru')

                return tr.translate()
            else:
                return text
        else:
            return text
    except Exception:
        return text

# Замена многигих пробелов на один
def squeeze(value):
    """Replace all sequences of whitespace chars with a single space."""
    return re.sub(r"[\x00-\x20]+", " ", value).strip()

RE_QUOPRI_BS = re.compile(r'\b=20=\n')
RE_QUOPRI_LE = re.compile(r'\b=\n')
RE_LONG_WORDS = re.compile(r'\b[\w\/\+\=\n]{72,}\b')

email.charset.ALIASES.update({
    'iso-8859-8-i': 'iso-8859-8',
    'x-mac-cyrillic': 'mac-cyrillic',
    'macintosh': 'mac-roman',
    'windows-874': 'cp874',
    # manually fix unknown charset encoding
    'default': 'utf-8',
    'x-unknown': 'utf-8',
    '%charset': 'utf-8',
})


def extract_body(msg, depth=0):
    """ Extract content body of an email messsage """
    try:
        body = []
        if msg.is_multipart():
            main_content = None
            # multi-part emails often have both
            # a text/plain and a text/html part.
            # Use the first `text/plain` part if there is one,
            # otherwise take the first `text/*` part.
            for part in msg.get_payload():
                is_txt = part.get_content_type() == 'text/*'
                if not main_content or is_txt:
                    main_content = extract_body(part)
                if is_txt:
                    break
            if main_content:
                body.extend(main_content)

        elif msg.get_content_type().startswith("text/"):
            # Get the messages
            charset = msg.get_param('charset', 'utf-8').lower()
            # update charset aliases
            charset = email.charset.ALIASES.get(charset, charset)
            msg.set_param('charset', charset)
            try:
                body.append(msg.get_content())
            except AssertionError as e:
                logging.critical('Ошибка parser_msg.py AssertionError в функции extract_body: {}'.format(e))
            except LookupError:
                # set all unknown encoding to utf-8
                # then add a header to indicate this might be a spam
                msg.set_param('charset', 'utf-8')
                body.append('=== Unknown encoding, possibly spam ===')
                body.append(msg.get_content())
        return body
    except Exception as e:
        logging.critical('Ошибка в parser_msg.py функции extract_body: {}'.format(e))

def normalize_text(body):
    try:
        body = re.sub(u"[.,\-\s]{3,}", " ", body)
        test = body.split(' ')
        words = []
        for line in test:
            if not line == '' or not line == ' ':
                if regex.search(r'[A-Za-z]', line) and regex.search(r'[А-Яа-яЁё]', line):
                    line = line.lower()
                    for key in dictionary.items():
                        i, j = key
                        line = re.sub(r'{}'.format(i), '{}'.format(j), line)
                    words.append(line)
                else:
                    words.append(line)
        return words
    except Exception as e:
        print('Пустая строка', e)

def serach_ip(msg):
    ip = ''
    for line in msg.get_all('Received'):
        pattern = re.compile("(127.0.0.1|192.168.10.|localhost)")
        match = pattern.search(line)
        if not match:
            # находим IP адреса и кол-во их повторов
            text_result = re.findall(r'\[([^\[\]]+)\]', line)
            # print(text_result)
            result = re.search(r'([0-9]{1,3}\.){3}[0-9]{1,3}', ' '.join(text_result))
            if result:
                ip = result.group(0)
    return ip

def read_emails(dirpath):
    """ Read all emails under a directory
    Returns:
      a iterator. Use
          for x in read_emails():
              print(x)
      to access the emails.
    """
    try:
        dirpath = os.path.expanduser(dirpath)
        for filename in iglob(dirpath):
            if not os.path.exists(filename):
                print("Ошибка открытия файла")
            else:
                msg = message_from_binary_file(open(filename, 'rb'), policy=policy.default)
                body = ' '.join(extract_body(msg))
                # remove potential quote print formatting strings
                body = RE_QUOPRI_BS.sub('', body)
                body = RE_QUOPRI_LE.sub('', body)
                body = RE_LONG_WORDS.sub('', body)
                body = cleanhtml(body)
                body = body.replace("\n", " ").replace("\r", " ").replace("\t", " ")\
                    .replace("\xa0", " ").replace("_", " ").replace("nbsp", " ")

                subject = ''
                if re.search('=== Unknown encoding, possibly spam ===', body):
                    subject += '[SPAM] '
                    body = re.sub('=== Unknown encoding, possibly spam ===', '', body)

                # здесь надо определить язык и перевести если надо
                subject = msg['subject']

                #body = translate(body)
                # Удаляем гиперссылки
                body = re.sub(urls, ' ', body)
                #print(detect_langs(body), body)
                if regex.search(r'[A-Za-z]', body) or regex.search(r'[А-Яа-яЁё]', body):
                    if detect(body) == 'ru':
                        # Нормализуем измененный текст
                        body = ' '.join(normalize_text(body))
                # Удалить все числа из текста
                body = re.sub(u"[^а-яА-ЯЁё.,\-\s]", " ", body)
                body = re.sub(u"[.,\-\s]{3,}", " ", body)
                # Чистим от всего лишнего

                body = squeeze(body)
                # Удалить все числа из текста

                ip = serach_ip(msg)

                yield {
                    "subject": subject,
                    "text": body or '',
                    "ip": ip,
                    'from': parseaddr(msg.get('From'))[1],
                    'to': parseaddr(msg.get('To'))[1],
                    'spam_or_no_spam': False,
                    'old_spam': None,
                    'date': d
                }
    except Exception as e:
        print("Ошибка", e)

def read_email(filename):
    try:
        if not os.path.exists(filename):
            return print("Ошибка открытия файла")
        else:
            f = open(filename, 'rb').readlines()
            for i in [0, 0, 0, 0, 0, 0]:
                f.pop(i)
            with open('{}.temp'.format(filename), 'wb') as F:
                F.writelines(f)

            msg = message_from_binary_file(open('{}.temp'.format(filename), 'rb'), policy=policy.default)

            body = ' '.join(extract_body(msg))
            # remove potential quote print formatting strings
            body = RE_QUOPRI_BS.sub('', body)
            body = RE_QUOPRI_LE.sub('', body)
            body = RE_LONG_WORDS.sub('', body)
            body = cleanhtml(body)
            body = body.replace("\n", " ").replace("\r", " ").replace("\t", " ") \
                .replace("\xa0", " ").replace("_", " ").replace("nbsp", " ")

            subject = ''
            if re.search('=== Unknown encoding, possibly spam ===', body):
                subject += '[SPAM] '
                body = re.sub('=== Unknown encoding, possibly spam ===', '', body)

            # здесь надо определить язык и перевести если надо
            subject = msg['subject']

            # body = translate(body)
            body = re.sub(urls, ' ', body)

            # Нормализуем измененный текст
            body = ' '.join(normalize_text(body))

            # Удалить все числа из текста
            body = re.sub(u"[^а-яА-Я.,\-\s]", " ", body)
            body = re.sub(u"[.,\-\s]{3,}", " ", body)
            # Чистим от всего лишнего
            body = squeeze(body)

            ip = serach_ip(msg)

            #(text, ip, mail_from, rcpt_to, spam_or_no_spam, date)
            emal_message = {
                "subject": subject,
                "text": body or '',
                "ip": ip,
                'from': parseaddr(msg.get('From'))[1],
                'to': parseaddr(msg.get('To'))[1],
                'spam_or_no_spam': False,
                'old_spam': None,
                'date': dn
            }

            os.remove('{}.temp'.format(filename))
            return emal_message
    except Exception as e:
        logging.critical('Ошибка в parser_msg.py функции read_email: {}'.format(e))
        #print('Ошибка в parser_msg.py функции read_email: {}'.format(e))

if __name__ == '__main__':
    #print(read_email(os.path.join(basedir + '\\mail\\spam\\3дрaвсmвуйme! Baс инmeрeсуюm клиeнmскиe бaзы дaнных  2019-01-17 0812.eml')))
    # Парсим папку с не спамом

    for mail in read_emails(os.path.join(basedir + '\\mail\\no_spam\\*.eml')):
        if not mail['text'] == '':
            storage.insert_mail(mail['subject'], mail['text'], mail['ip'],
                                mail['from'], mail['to'], False,
                                mail['old_spam'], mail['date'])
    
            print(mail['text'])


    # Парсим папку со спамом
    for mail in read_emails(os.path.join(basedir + '\\mail\\spam\\*.eml')):
        if not mail['text'] == '':
            storage.insert_mail(mail['subject'], mail['text'], mail['ip'],
                                mail['from'], mail['to'], True,
                                mail['old_spam'], mail['date'])
            print(mail['text'])

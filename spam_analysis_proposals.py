# -*- coding: utf-8 -*-
# imports
import string
import logging, os, sys
import math
import re
import pandas as pd
from collections import Counter
from db.models import session, engine
from db.controller import Storage
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import datetime
from langdetect import detect, detect_langs

d = datetime.datetime.now()
dn = d.strftime("%Y-%m-%d")

FOLDER_PATH_SPAMFILTER = "d:\\CommuniGate Files\\SpamFilter\\"
FOLDER_PATH_LOG = "d:\\CommuniGate Files\\SpamFilter\\SpamFilterLog\\"
PATH_LOG = os.path.join(FOLDER_PATH_LOG, '{}.log'.format(dn))

logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG,
                    filename=PATH_LOG)

storage = Storage(session)

spam = []
not_spam = []
csv_file = os.path.join(FOLDER_PATH_SPAMFILTER, 'spam_proposals_training.csv')
#csv_file = 'spam_proposals_training.csv'

#nltk.download()
spam_words = []
not_spam_words = []


main_table = pd.DataFrame({
        'word': [],
        'spam': [],
        'no_spam': [],
        'probability_of_spam': [],
        'probability_not_spam': []
    })

garbagelist = [u'спасибо', u'пожалуйста', u'добрый', u'день', u'вечер',u'заявка', u'прошу', u'доброе', u'утро']

def splitstring(str):
    words = []
    #разбиваем строку по символам из []
    for i in re.split('[;,.,\n,\s,:,-,+,(,),=,/,«,»,@,\d,!,?,"]', str):
        #берём только "слова" длиной 2 и более символов
        if len(i) > 1:
            #не берем слова-паразиты
            if i in garbagelist:
                pass
            else:
                words.append(i)
    return words

def tokenize_ru(file_text):
    try:
        # firstly let's apply nltk tokenization
        tokens = splitstring(file_text.lower())

        # let's delete punctuation symbols
        tokens = [i for i in tokens if (i not in string.punctuation)]

        # deleting stop_words
        stop_words = stopwords.words('russian')
        stop_words.extend(['что', 'это', 'так', 'вот', 'быть', 'как', 'в', '—', '–', 'к', 'на', '...'])
        tokens = [i for i in tokens if (i not in stop_words)]

        # cleaning words
        tokens = [i.replace("«", "").replace("»", "") for i in tokens]
        tokens = [i for i in tokens if not (len(i) == 1)]

        return tokens
    except Exception as e:
        logging.critical('Ошибка в spam_analysis_proposals.py функции tokenize_me: {}'.format(e))

# Создаем функцию подсчета вероятности вхождения слова Xi в документ класса Qk
def formula_1(N_ik, M, N_k):
    #print("({} + {}) / ({} + {})".format(1, N_ik, M, N_k))
    try:
        return (1+N_ik)/(M+N_k)
    except ZeroDivisionError as e:
        logging.critical(
            'Ошибка в spam_analysis_proposals.py функции formula_1, деления на ноль, вероятно таблица пуста: {}'.format(e))
    except Exception as e:
        logging.critical('Ошибка в spam_analysis_proposals.py функции formula_1: {}'.format(e))

def training():
    try:
        # Обучаюшая выборка со спам письмами:
        for i in storage.select_mail(spam_or_no_spam=True):
            spam.append(i.text)

        # Обучающая выборка с не спам письмами:
        for i in storage.select_mail(spam_or_no_spam=False):
            not_spam.append(i.text)
        # ---------------Для спама------------------
        for line in spam:
            spam_words.extend(tokenize_ru(line))

        # Создаем таблицу с уникальными словами и их количеством
        unique_words = Counter(spam_words)

        # ---------------Для не спама------------------
        for line in not_spam:
            spam_words.extend(tokenize_ru(line))

        main_table['word'] = tuple(unique_words.keys())
        main_table['spam'] = tuple(unique_words.values())
        main_table['no_spam'] = [0 for x in range(len(tuple(unique_words.values())))]

        for i in range(len(not_spam_words)):
            # Создаем логическую переменную
            need_word = True
            for j in range(len(main_table.index)):
                # Если "не спам" слово существует, то к счетчику уникальных слов +1
                if not_spam_words[i] == main_table.loc[j, 'word']:
                    main_table.loc[j, "no_spam"] = main_table.loc[j, "no_spam"] + 1
                    need_word = False
            # Если слово не встречалось еще, то добавляем его в конец data frame и создаем счетчики
            if need_word:
                main_table.loc[len(main_table.index)] = [not_spam_words[i], 0, 1, pd.np.nan, pd.np.nan]
        main_table.to_csv(csv_file)
    except Exception as e:
        logging.critical('Ошибка в spam_analysis_proposals.py функции training: {}'.format(e))

def analysis(main_table, test_letter):
    try:
        # Считаем количество слов из обучающей выборки
        quantity = len(main_table.index)
        test_letter_list = []
        # ---------------Для проверки------------------
        sentences = [tokenize_ru(sent) for sent in sent_tokenize(test_letter, 'russian')]
        for i in sentences:
            test_letter_list.append(' '.join(i))

        for i in range(len(test_letter_list)):
            # Используем ту же логическую переменную, чтобы не создавать новую
            need_word = True
            for j in range(len(main_table.index)):
                # Если слово из проверочного письма уже существует в нашей выборке то считаем вероятность каждой категории
                if test_letter_list[i] == main_table.loc[j, 'word']:
                    main_table.loc[j, 'probability_of_spam'] = formula_1(main_table.loc[j, 'spam'], quantity, sum(main_table['spam']))
                    main_table.loc[j, 'probability_not_spam'] = formula_1(main_table.loc[j, 'no_spam'], quantity, sum(main_table['no_spam']))
                    need_word = False
            # Если слова нет, то добавляем его в конец data frame, и считаем вероятность спама/не спама
            if need_word:
                main_table.loc[len(main_table.index)] = [test_letter_list[i], 0, 0,
                formula_1(0, quantity, sum(main_table['spam'])),
                formula_1(0, quantity, sum(main_table['no_spam']))]


        # Переменная для подсчета оценки класса "Спам"
        probability_spam = 1

        # Переменная для подсчета оценки класса "Не спам"
        probability_not_spam = 1

        # Переменная для подсчета оценки класса "Спам"
        probability_spam_log = 1

        # Переменная для подсчета оценки класса "Не спам"
        probability_not_spam_log = 1

        for i in range(len(main_table.index)):
            if not main_table.loc[i, 'probability_of_spam'] is None and not pd.isnull(
                    main_table.loc[i, 'probability_of_spam']):
                # Шаг 1.1 Определяем оценку того, что письмо - спам
                probability_spam = probability_spam * main_table.loc[i, 'probability_of_spam']
            if not main_table.loc[i, 'probability_not_spam'] is None and not pd.isnull(
                    main_table.loc[i, 'probability_not_spam']):
                # Шаг 1.2 Определяем оценку того, что письмо - не спам
                probability_not_spam = probability_not_spam * main_table.loc[i, 'probability_not_spam']
        #probability_spam = probability_spam * (2/4)
        #probability_not_spam = probability_not_spam * (2/4)

        # Шаг 2.1 Определяем оценку того, что письмо - спам
        probability_spam = (main_table['spam'].sum() / (main_table['spam'].sum() + main_table['no_spam'].sum())) * probability_spam

        # Шаг 2.2 Определяем оценку того, что письмо - не спам
        probability_not_spam = (main_table['no_spam'].sum() / (main_table['spam'].sum() + main_table['no_spam'].sum())) * probability_not_spam

        logging.debug("Оценка для категории «Спам»: {} Оценка для категории «Не спам»: {}".format(probability_spam, probability_not_spam))
        logging.debug("Оценка для категории «Спам»: {} Оценка для категории «Не спам»: {}".format(math.log(probability_spam), math.log(probability_not_spam)))

        spam_count = (probability_spam / probability_not_spam) * (math.log(probability_spam) / math.log(probability_not_spam))
        # Чья оценка больше - тот и победил
        if probability_spam > probability_not_spam:
            return True, spam_count
        else:
            return False, spam_count
    except Exception as e:
        logging.critical('Ошибка в spam_analysis_proposals.py функции analysis: {}'.format(e))
        return 'ERROR'

def spam_analysis_main(test_letter):
    try:
        if detect(test_letter) == 'ru':
            if not os.path.isfile(csv_file):
                training()

            df = pd.read_csv(csv_file)
            main_table = df.copy()
            return analysis(main_table, test_letter)
        else:
            return True, 100
    except Exception as e:
        logging.critical('Ошибка в spam_analysis_proposals.py функции spam_analysis_main: {}'.format(e))

if __name__ == '__main__':
    #test_letter = "В магазине гора яблок. Купи семь килограмм и шоколадку"
    #test_letter = 'Путевки по низкой цене'
    test_letter = 'Завтра состоится собрание'
    if not os.path.isfile(csv_file):
        print('тренировка')
        training()
    df = pd.read_csv(csv_file)

    main_table = df.copy()
    #print(main_table)
    print(analysis(main_table, test_letter))
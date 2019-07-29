import re
from langdetect import detect, detect_langs

text_pars = [
    '3qравсmвyйme Bас uнmeрeсyюm клueнmскue базы qанныx?',
    '3дрaвcmвyйmе! Вac uнmереcyюm клuенmcкuе бaзы дaнныx?',
    '3дрaвсmвуйme! Baс uнmeрeсуюm клueнmскue бaзы дaнных?',
    '3дрaвсmвуйme! Baс инmeрeсуюm клиeнmскиe бaзы дaнных',
    'Zdravstvujte vas interesuyut klientskie bazy dannyh?'
]

"""
3qравсmвyйme bас uнmeрeсyюm клueнmскue базы qанныx
3дрaвcmвyйmе вac uнmереcyюm клuенmcкuе бaзы дaнныx
3дрaвсmвуйme baс uнmeрeсуюm клueнmскue бaзы дaнных
3дрaвсmвуйme baс инmeрeсуюm клиeнmскиe бaзы дaнных
"""



dictionary = {
    '3': 'з',
    'm': 'т',
    '0': 'о',
    'u': 'и',
    'q': 'д',
    'b': 'в',
    'a': 'а',
    'p': 'р',
    'y': 'у',
    'e': 'е',
    'k': 'к',
    'o': 'о',
}


for text in text_pars:
    print(detect_langs(text))
    if detect(text) == 'ru':
        text = text.lower()
        for key in dictionary.items():
            i, j = key
            text = re.sub(r'{}'.format(i), '{}'.format(j), text)
        print(text)



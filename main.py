import logging
from telegram.ext import Updater, MessageHandler, Filters
from telegram.ext import CommandHandler
from telegram import ReplyKeyboardMarkup
import bisect
import requests
import json

markup_start = ReplyKeyboardMarkup([['/go']], one_time_keyboard=True)
markup_go_friend = ReplyKeyboardMarkup([['/yes', '/no']], one_time_keyboard=True)

markup_start = ReplyKeyboardMarkup([['/go']], one_time_keyboard=True)
markup_go_friend = ReplyKeyboardMarkup([['/yes', '/no']], one_time_keyboard=True)


class Game_board:

    def prov(s, n):

        s = str(s)
        for i in s:
            if i not in map(str, range(10)):
                return False
        if len(s) != n:
            print(2)
            return False
        if len(set(list(s))) != n:
            print(3)
            return False
        if '0' == s[0]:
            print(45)
            return False
        return True

    class Answer:

        def __init__(self, b_count=0, k_count=0):
            self.b_count = b_count
            self.k_count = k_count

        def __str__(self):
            return f'быков:{self.b_count};коров:{self.k_count}'

    def count(a, b):
        b_count = 0
        k_count = 0
        for i in range(len(a)):
            if a[i] == b[i]:
                b_count += 1
            elif a[i] in b:
                k_count += 1
        return Game_board.Answer(b_count, k_count)


class Person:

    def __init__(self, update, context):
        self.update, self.context = update, context
        self.index = None
        self.friend = None
        self.zapros = None
        self.friends = []
        self.records = {'поражения': 0, 'ничьи': 0, 'победы': 0}

    def free(self):
        return self.index == None

    def name(self):
        return self.update.message.chat.username

    def __str__(self):
        return str(self.__dict__)

    def do(self):
        if self.zapros != None:
            self.zapros()

    def clear_zapros(self):
        self.friend = None
        self.zapros = None


class Pair:

    def __init__(self, person1: Person, person2: Person):
        self.person1 = person1
        self.person2 = person2
        self.persons = [self.person1, self.person2]
        self.key = f'{get_name(self.person1)}@{get_name(self.person2)}'
        self.quiz1 = None
        self.quiz2 = None
        self.queue_number = 0
        self.count_xod = 0

    # фуннкциф возрващающая противника
    def enemy(self, update):
        if self.person1.update.message.chat.username == update.message.chat.username:
            return self.person2
        if self.person2.update.message.chat.username == update.message.chat.username:
            return self.person1

    def quiz(self, update):
        if self.person1.update.message.chat.username == update.message.chat.username:
            return self.quiz2
        if self.person2.update.message.chat.username == update.message.chat.username:
            return self.quiz1

    def number(self, update):
        if self.person1.update.message.chat.username == update.message.chat.username:
            return 0
        if self.person2.update.message.chat.username == update.message.chat.username:
            return 1

    def number_queue(self, update):
        return self.number(update) == self.queue_number

    def message(self, s, update):
        self.enemy(update).update.message.reply_text(str(s))

    def __str__(self):
        return f'{self.person1.name()}:{self.person2.name()},{self.free_xod()}.{self.quiz1},{self.quiz2}'

    def xod(self, update, ans=None, text=None):
        if self.free_xod():
            self.count_xod += 1
            self.queue_number += 1
            self.queue_number %= 2
            self.message(f'Ваш противник сходил так: {text}: {str(ans)}.', update)

    def finish(self, draw=False):
        if draw:
            self.person1.update.message.reply_text('Поздравляем с Ничьёй!')
            self.person2.update.message.reply_text('Поздравляем с Ничьёй!')
            return {get_name(self.person1): 1, get_name(self.person1): 1}
        if self.count_xod % 2 == 1:
            self.person2.update.message.reply_text('Поздравляем с победой')
            self.person1.update.message.reply_text(
                f'Увы, Вы проиграли, но не расстраивайтесь, в следующий раз Вам повезёт).\n'
                f'Число Вашего противника: {self.quiz2}')
            return {get_name(self.person1): 2, get_name(self.person1): 0}
        else:
            self.person1.update.message.reply_text('Поздравляем с победой')
            self.person2.update.message.reply_text(
                f'Увы, Вы проиграли, но не расстраивайтесь, в следующий раз Вам повезёт).\n'
                f'Число Вашего противника: {self.quiz1}')
            return {get_name(self.person1): 9, get_name(self.person1): 2}

    def free_xod(self):
        return not (None in (self.quiz1, self.quiz2))

    def put_quiz(self, update, quiz):
        if get_name(self.person1) == get_name(update) and self.quiz1 == None:
            self.quiz1 = quiz
        if get_name(self.person2) == get_name(update) and self.quiz2 == None:
            self.quiz2 = quiz
        if self.free_xod():
            self.person1.update.message.reply_text('Игра началась. Ваш ход.')
            self.person2.update.message.reply_text('Игра началась. Ждём когда первый игрок сходит.')


def get_name(update):
    if type(update) == str:
        return Game_info.name(None, update)
    if type(update) == Person:
        update = update.update
    name = update.message.chat.username
    if name == None:
        return update.message.chat.id
    else:
        return name


class Game_info:

    def __init__(self):
        self.free = True
        self.free_name = None
        self.key = 0
        self.persons = dict()
        self.pairs = dict()
        self.N = 4
        self.win_ball = 10
        self.draw_ball = 5
        self.keys_records = ['поражения', 'ничьи', 'победы']

    def put(self, update, context):
        self.free = False
        self.free_name = self.person_get(update)
        self.person_get(update).index = None

    def find_game(self, update, context):
        person = self.free_name
        person_new = self.person_get(update)
        self.free = True
        self.free_name = None
        self.find_game_add(person, person_new)

    def find_game_add(self, person, person_new):
        self.find_game_message(person)
        self.find_game_message(person_new)
        self.append_pair(person, person_new)

    def find_game_message(self, person):
        person.update.message.reply_text('Игра найдена.\nЗагадайте, пожалуйста Ваше число.')

    def person_put_game(self, person1, person2):
        self.persons[get_name(person1)].index = person2

    def append_pair(self, person1, person2):
        pair = Pair(person1, person2)
        self.pairs[pair.key] = pair
        self.person_put_game(person1, pair.key)
        self.person_put_game(person2, pair.key)

    def append_person(self, update, context):
        if get_name(update) not in self.persons:
            self.persons[get_name(update)] = Person(update, context)
        return Person(update, context)

    def person_free(self, update):
        return self.person_get(update).free()

    def person_get(self, update, contex=None):
        return self.persons.get(get_name(update), self.append_person(update, contex))

    def person_get_game(self, update):
        return self.person_get(update)

    def person_put_free(self, update):
        self.persons[get_name(update)].index = None

    def person_key(self, update):
        return self.persons[get_name(update)].index

    def get_pair(self, update):
        return self.pairs[self.person_key(update)]

    def pair_quiz(self, update):
        return self.get_pair(update).quiz(update)

    def pair_queue_number(self, update):
        return self.get_pair(update).number_queue(update)

    def pair_xod(self, update, ans, text):
        self.pairs[self.person_key(update)].xod(update, ans, text)

    def free_pair(self, pair):
        self.person_put_free(pair.person1)
        self.person_put_free(pair.person2)

    def pair_finish(self, update, draw=False):
        rec = self.get_pair(update).finish(draw)
        pair = self.get_pair(update)
        key = self.person_key(update)
        self.free_pair(pair)
        del self.pairs[key]
        self.save_record(rec)

    def save_record(self, rec):
        for i in rec:
            self.person_get(i).records[self.keys_records[rec[i]]] += 1

    def pair_free_xod(self, update):
        return self.get_pair(update).free_xod()

    def pair_put_quiz(self, update, text):
        self.pairs[self.person_key(update)].put_quiz(update, text)

    def name(self, name):
        name = name.strip()
        print(''.join(name.split('@')))
        return ''.join(name.split('@'))

    def get_zapros(self, update, name):
        self.persons[self.name(name)].update.message.reply_text(f'Вас пригласил игрок {get_name(update)}, '
                                                                f'если хотите с ним играть то нажмите на одну из кнопок /yes или /n.',
                                                                reply_markup=markup_go_friend)
        self.persons[self.name(name)].friend = get_name(update)

    def zapros(self, update, name):
        name = self.name(name)
        self.person_get(update).friend = name
        function = lambda: self.get_zapros(update, name)
        self.persons[name].zapros = function
        self.persons[name].friend = self.person_get(update)
        if self.persons[name].free():
            self.persons[name].do()

    def clear_zapros(self, update):
        self.persons[get_name(self.get_friend(update))].clear_zapros()
        self.persons[get_name(update)].clear_zapros()

    def if_friend(self, update):
        return self.person_get(update).friend != None

    def get_friend(self, update):
        if self.if_friend(update):
            return self.person_get(self.person_get(update).friend)

    def end_draw(self, update):
        self.pair_finish(update, True)


INFO = Game_info()


def start(update, context):
    global INFO
    print(get_name(update))
    INFO.append_person(update, context)
    update.message.reply_text(f'''
Привет!
Это бот-игра "Быки и коровы".

Правила игры Вы можете найти по ссылке: https://urok.1sept.ru/articles/662278.
Мы будем играть с четырехзначными числами.
Чтобы начать, введите команду /go. 
Когда Ваш противник будет найден, введите загадываемое число.

После этого Вы и Ваш противник будете по очереди пытаться отгадать число; отгадавший его первым выигрывает.
Если хотите сыграть с другом наберите /f никнейм вашего друга в телеграмме.
Если хотите выйти,

 Удачной игры!
    ''',
                              reply_markup=markup_start
                              )


def go(update, context):
    global INFO
    URL = 'http://127.0.0.1:5000/'
    response = requests.post(URL + 'users/' + get_name(update))
    print(response.content)
    INFO.append_person(update, context)
    if INFO.person_free(update):
        update.message.reply_text('Ищем соперника',
                                  reply_markup=markup_start
                                  )
        if INFO.if_friend(update):
            update.message.reply_text('Ваши запросы отменены')
            INFO.clear_zapros(update)
        if INFO.free:
            INFO.put(update, context)
            INFO.free = False
        else:
            INFO.find_game(update, context)
    else:
        update.message.reply_text(f'Вы уже играете с {get_name(INFO.get_pair(update).enemy(update))}')


def go_friend(update, name):
    global INFO
    INFO.zapros(update, name)


def text_handler(update, context):
    global INFO
    if not INFO.person_free(update):
        if INFO.pair_free_xod(update):
            if INFO.pair_queue_number(update):
                if Game_board.prov(update.message.text, INFO.N):
                    update.message.reply_text('Ход сделан')
                    ans = Game_board.count(update.message.text, INFO.pair_quiz(update))
                    if ans.b_count == INFO.N:
                        update.message.reply_text('Вы выиграли')
                        INFO.pair_finish(update)
                    else:
                        update.message.reply_text(str(ans))
                        INFO.pair_xod(update, str(ans), update.message.text)
                else:
                    update.message.reply_text('Некоректный запрос')

            else:
                update.message.reply_text('Не Ваша очерердь')
        else:
            if Game_board.prov(update.message.text, INFO.N):
                INFO.pair_put_quiz(update, update.message.text)
                update.message.reply_text(f'Вы загадали число {update.message.text}')
            else:
                update.message.reply_text('Некоректное загадываемое число')
    else:
        s = update.message.text.split()
        if s[0] == '/f':
            go_friend(update, s[1])


def yes(update, context):
    global INFO
    if INFO.if_friend(update):
        INFO.find_game_add(INFO.get_friend(update), INFO.person_get(update))
        INFO.get_friend(update).update.message.reply_text('Вас запрос был принят!')
        INFO.clear_zapros(update)
    else:
        update.message.reply_text('Вам никто не  не кидал приглашение на игру!')


def no(update, context):
    global INFO
    if INFO.if_friend(update):
        INFO.clear_zapros(update)
        INFO.get_friend(update).update.message.reply_text('Вас запрос был отклонён!')
    else:
        update.message.reply_text('Вам никто не  не кидал приглашение на игру!')


def end(update, context):
    global INFO
    INFO.end_draw(update)


def record(update, context):
    rec = INFO.person_get(update).records
    update.message.reply_text(str(rec)[1:-1])


class Driver:

    def __init__(self):
        self.URL = 'http://127.0.0.1:5000/'

    def prob(self, update, context):
        global INFO
        print(type(update))

    def save(self, update, context=None):
        global INFO
        response = requests.post(self.url + 'users/' + get_name(update))

    def get(self, update, context):
        global INFO
        response = requests.get(self.url + 'users/' + get_name(update))

    def info(self, update, context):
        print(INFO.persons)
        for i in INFO.pairs:
            update.message.reply_text(f'{i}:{INFO.pairs[i]},{INFO.pairs[i].quiz1}:{INFO.pairs[i].quiz2}')
        for i in INFO.persons:
            update.message.reply_text(f'{i}\n{INFO.persons[i]}')

    def clear(self, update, context):
        global INFO
        INFO = Game_info()


TOKEN = 'token' # token


def main():
    updater = Updater(TOKEN)
    driver = Driver()
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("go", go))
    dp.add_handler(CommandHandler("prob", driver.prob))
    dp.add_handler(CommandHandler("save", driver.save))
    dp.add_handler(CommandHandler("get", driver.get))
    dp.add_handler(CommandHandler("info", driver.info))
    dp.add_handler(CommandHandler("clear", driver.clear))
    dp.add_handler(CommandHandler("yes", yes))
    dp.add_handler(CommandHandler("no", no))
    dp.add_handler(CommandHandler("end", end))
    dp.add_handler(CommandHandler("record", record))
    dp.add_handler(MessageHandler(Filters.text, text_handler))
    updater.start_polling()
    updater.idle()


main()
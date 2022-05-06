import logging
import os
import time
from lib2to3.pgen2.tokenize import TokenError

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN_1')
TELEGRAM_TOKEN = os.getenv('TOKEN_2')
TELEGRAM_CHAT_ID = os.getenv('ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/1'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s, %(lineno)s'
)


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Удачная отправка сообщения в Telegram!')
        return True
    except Exception:
        logging.error('Сбой при отправке сообщения в Telegram')
        return False


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        logging.error(f'Эндпоинт {ENDPOINT} недоступен. '
                      f'Код ответа API: {response.status_code}')
        raise Exception(f'Эндпоинт {ENDPOINT} недоступен.')
    return response.json()


def check_response(response):
    """Проверка ответа на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Тип данных ответа API отличается от ожидаемого')
    homeworks = response.get('homeworks')
    if not len(homeworks):
        raise KeyError('Список homeworks пустой')
    if not isinstance(homeworks, list):
        raise TypeError('Тип данных домашки отличается от ожидаемого')
    return homeworks


def parse_status(homework):
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        logging.error('Отсутствие ожидаемых ключей в ответе API')
        raise KeyError('Ошибка ключа \'homework_name\'')
    if homework_status is None:
        logging.error('Отсутствие ожидаемых ключей в ответе API')
        raise KeyError('Ошибка ключа \'status\'')
    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        logging.error('Недокументированный статус домашней работы')
        raise KeyError('Ошибка ключа \'status\' в HOMEWORK_STATUSES')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения"""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens:
        if token is None:
            logging.critical(f'Отсутствует обязательная переменная окружения: '
                             f'{token} Программа принудительно остановлена.')
            return False
        return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise TokenError('Функция check_tokens возвращает False')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    error_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks_list = check_response(response)
            if not homeworks_list:
                logging.debug('Обновлений по домашней работе нет')
            for homework in homeworks_list:
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'{message}')
            event = send_message(bot, message)
            if event:
                current_timestamp = int(time.time())
                error_message = message
            bot.send_message(TELEGRAM_CHAT_ID, error_message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

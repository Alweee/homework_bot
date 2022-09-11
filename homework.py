import logging
import os
import time
from http import HTTPStatus
from lib2to3.pgen2.tokenize import TokenError

import requests
import telegram
from dotenv import load_dotenv

from settings import ENDPOINT, HEADERS, HOMEWORK_STATUSES, RETRY_TIME

load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN_1')
TELEGRAM_TOKEN = os.getenv('TOKEN_2')
TELEGRAM_CHAT_ID = os.getenv('ID')

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s, %(lineno)s'
)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Удачная отправка сообщения в Telegram!')
    except telegram.TelegramError as error:
        logging.error(f'Сбой при отправке сообщения в Telegram: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logging.error(f'Сбой при запросе к эндпоинту {error}')
        raise (f'Сбой при запросе к эндпоинту {error}')
    if response.status_code != HTTPStatus.OK:
        logging.error(f'Эндпоинт {ENDPOINT} недоступен. '
                      f'Код ответа API: {response.status_code}')
        raise (f'Эндпоинт {ENDPOINT} недоступен.')
    try:
        return response.json()
    except Exception as error:
        raise (f'Невалидный формат json: {error}')


def check_response(response):
    """Проверка ответа на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Тип данных ответа API отличается от ожидаемого')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise('Ключа "homeworks" не существует')
    if not isinstance(homeworks, list):
        raise TypeError('Тип данных домашки отличается от ожидаемого')
    if not homeworks:
        logging.info('Список homeworks пустой')
    return homeworks


def parse_status(homework):
    """Извлекает информацию из конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        logging.error('Отсутствие ожидаемых ключей в ответе API')
        raise KeyError('Ошибка ключа \'homework_name\'')
    if homework_status is None:
        logging.error('Отсутствие ожидаемых ключей в ответе API')
        raise KeyError('Ошибка ключа \'status\'')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        logging.error('Недокументированный статус домашней работы')
        raise KeyError('Ошибка ключа \'status\' в HOMEWORK_STATUSES')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует обязательная переменная окружения, '
                         'программа принудительно остановлена.')
        raise TokenError('Функция check_tokens возвращает False')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 1549962000
    error_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks_list = check_response(response)
            if not homeworks_list:
                logging.debug('Обновлений по домашней работе нет')
            message = parse_status(homeworks_list[0])
            send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'{message}')
            if message != error_message:
                bot.send_message(TELEGRAM_CHAT_ID, message)
                error_message = message


if __name__ == '__main__':
    main()

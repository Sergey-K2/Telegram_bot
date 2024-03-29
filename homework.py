"""Бот-ассистент Практикум."""
import logging
import os
import sys
import time

from dotenv import load_dotenv
import telegram
import requests

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

# Pytest просит назвать именно HOMEWORK_VERDICTS
HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

TOKENS = ("PRACTICUM_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_TOKEN")

STATUS_CHANGED_MESSAGE = (
    'Изменился статус проверки работы "{homework_name}". {verdict}'
)
SUCCESSFUL_SENDING_MESSAGE = "Сообщение в Telegram отправлено: {message}"
SENDING_ERROR_MESSAGE = (
    "Сообщение {message} в Телеграм не отправлено. Произошла ошибка {error}"
)
REQUESTS_PROBLEMS_MESSAGE = (
    "Ошибка запроса {error}. Параметры запроса: {url}, {headers}, {params}."
)
RESPONSE_ISNT_200_MESSAGE = (
    "Ответ сервера не 200."
    "Получен ответ {status_code}. Параметры запроса:"
    "{url}, {headers}, {params}. Сообщение сервера:"
    "{message}."
)
HOMEWORK_KEY_ERROR_MESSAGE = 'Нет ключа "homework_name"'
STATUS_KEY_ERROR_MESSAGE = 'Не удалось получить статус по ключу "status"'
UNKNOWN_STATUS = "Проучен неихвестный статус: {status}"
ERROR_MESSAGE_IN_MAIN = "Сбой в работе программы: {error}"
ERRORS_IN_API_RESPONSE = (
    "В ответе API обнаружились ошибка: {error}. Параметры запроса: {url},"
    "{headers}, {params}. Ключ: {key}."
)
RESPONSE_ISNT_DICTIOANARY_MESSAGE = (
    "В ответе API вместо словаря получен {type}"
)
NO_HOMEWORK_KEY_MESSAGE = 'Нет ключа "homeworks"'
VALUE_ISNT_LIST_MESSAGE = 'Значение по ключу "homework" не список, а {type}'


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправка сообщения c обновленным стуатусом в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(SUCCESSFUL_SENDING_MESSAGE.format(message=message))
        return True
    except telegram.TelegramError as error:
        logger.error(
            SENDING_ERROR_MESSAGE.format(message=message, error=error),
            exc_info=True,
        )
        return False


def get_api_answer(current_timestamp):
    """Делаем запрос к API."""
    request_data = dict(
        url=ENDPOINT,
        headers=HEADERS,
        params={"from_date": current_timestamp},
    )

    try:
        response = requests.get(**request_data)
    except requests.exceptions.RequestException as error:
        raise ConnectionError(
            REQUESTS_PROBLEMS_MESSAGE.format(error=error, **request_data)
        )

    if response.status_code != 200:
        raise exceptions.ResponseIsnt200Error(
            RESPONSE_ISNT_200_MESSAGE.format(
                status_code=response.status_code,
                message=response.get("message"),
                **request_data,
            )
        )
    api_response = response.json()
    keys = ("code", "error")
    for key in keys:
        if key in api_response:
            raise Exception(
                ERRORS_IN_API_RESPONSE.format(
                    key=key,
                    error=api_response.get(key),
                    **request_data,
                )
            )
        return api_response


def check_response(response):
    """Проверяем ответ API."""
    if not isinstance(response, dict):
        raise TypeError(
            RESPONSE_ISNT_DICTIOANARY_MESSAGE.format(type=type(response))
        )
    if "homeworks" not in response.keys():
        raise KeyError(NO_HOMEWORK_KEY_MESSAGE)
    homeworks = response.get("homeworks")
    if not isinstance(homeworks, list):
        raise TypeError(VALUE_ISNT_LIST_MESSAGE.format(type=type(homeworks)))
    return homeworks


def parse_status(homework):
    """Получаем статус API для сообщения."""
    try:
        homework_name = homework["homework_name"]
    except KeyError:
        raise KeyError(HOMEWORK_KEY_ERROR_MESSAGE)
    try:
        status = homework["status"]
    except KeyError:
        raise KeyError(STATUS_KEY_ERROR_MESSAGE)
    if status not in HOMEWORK_VERDICTS.keys():
        raise ValueError(UNKNOWN_STATUS.format(status=status))
    return STATUS_CHANGED_MESSAGE.format(
        homework_name=homework_name, verdict=HOMEWORK_VERDICTS.get(status)
    )


def check_tokens():
    """Проверка доступности переменных окружения."""
    token_flag = True
    for token in TOKENS:
        if globals()[token] is None:
            logging.critical(f"Проверка токена {token} не пройдена")
            token_flag = False
    return token_flag


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        return
    logger.info("Токены получены, бот запущен")
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            status = parse_status(homeworks[0])
            if send_message(bot, status):
                current_timestamp = response.get(
                    "current_date", current_timestamp
                )

        except Exception as error:
            message = ERROR_MESSAGE_IN_MAIN.format(error=error)
            send_message(bot, message)
            logger.error(message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()

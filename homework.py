"""Бот-ассистент Практикум."""
import logging
import os
import sys
import time

import requests
from dotenv import load_dotenv
import telegram
import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"{PRACTICUM_TOKEN}"}

# Pytest просит назвать именно HOMEWORK_VERDICTS
HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

STATUS_CHANGED_MESSAGE = (
    'Изменился статус проверки работы "{homework_name}". {verdict}'
)
SUCCESSFUL_SENDING_MESSAGE = "Сообщение в Telegram отправлено: {message}"
REQUESTS_PROBLEMS_MESSAGE = (
    "Ошибка запроса. Параметры запроса: {endpoint}," "{headers}, {params}."
)
RESPONSE_ISNT_200_MESSAGE = (
    "Ответ сервера не 200."
    "Получен ответ {status_code}. Параметры запроса:"
    "{endpoint}, {headers}, {current_timestamp}. Сообщение сервера:"
    '{response.get("message")}'
)
HOMEWORK_KEY_ERROR_MESSAGE = 'Нет ключа "homework_name"'
STATUS_KEY_ERROR_MESSAGE = 'Не удалось получить статус по ключу "status"'
UNKNOWN_STATUS = "Проучен неихвестный статус: {status}"
ERROR_MESSAGE_IN_MAIN = "Сбой в работе программы: {error}"

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
    except telegram.TelegramError as error:
        logger.error(
            f"Сообщение в Телеграм не отправлено." f"Произошла ошибка {error}",
            exc_info=True,
        )


def get_api_answer(current_timestamp):
    """Делаем запрос к API."""
    request_data = {
        "headers": HEADERS,
        "params": {"from_date": current_timestamp},
    }
    try:
        response = requests.get(ENDPOINT, **request_data)
    except Exception:
        raise exceptions.SomethingWrongWithRequestError(
            REQUESTS_PROBLEMS_MESSAGE.format(
                endpoint=ENDPOINT,
                headers=request_data.get("headers"),
                params=request_data.get["params"],
            )
        )

    if response.status_code != 200:
        raise exceptions.ResponseIsnt200Error(
            RESPONSE_ISNT_200_MESSAGE.format(
                status_code=response.status_code,
                endpoint=ENDPOINT,
                headers=HEADERS,
                current_timestamp=current_timestamp,
            )
        )

    if (
        response.json().get("code") is not None
        or response.json().get("error") is not None
    ):
        return (
            f'Ошибки в ответе сервера: {response.json().get("error")},'
            f'{response.json().get("code")}'
        )
    return response.json()


def check_response(response):
    """Проверяем ответ API."""
    if not isinstance(response, dict):
        raise exceptions.ResponseIsntDictionaryError
    try:
        homeworks = response.get("homeworks")
    except KeyError:
        raise KeyError("Нет ключа 'homeworks'")

    if not isinstance(homeworks, list):
        raise TypeError(
            f"По ключу 'homeworks' получен объект формата" f"{type(homeworks)}"
        )
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
        raise KeyError(UNKNOWN_STATUS.format(status=status))
    verdict = HOMEWORK_VERDICTS.get(status)
    return STATUS_CHANGED_MESSAGE.format(
        homework_name=homework_name, verdict=verdict
    )


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = ("PRACTICUM_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_TOKEN")
    token_flag = True
    for token in tokens:
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
            send_message(bot, status)
            current_timestamp = response.get("current_date", current_timestamp)

        except Exception as error:
            send_message(bot, ERROR_MESSAGE_IN_MAIN.format(error=error))
            logger.error(ERROR_MESSAGE_IN_MAIN.format(error=error))

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()

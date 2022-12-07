"""Бот-ассистент Практикум."""
import logging
import os
import sys
import telegram
import time
import requests

from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

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
    except telegram.TelegramError as error:
        logger.error(f"Сообщение в Telegram не отправлено: {error}")
    else:
        logger.debug(f"Сообщение в Telegram отправлено: {message}")


def get_api_answer(current_timestamp):
    """Делаем запрос к API."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={"from_date": current_timestamp or int(time.time())},
        )
    except requests.exceptions.RequestException:
        logger.error("Ошибка запроса")

    if response.status_code != 200:
        message_response = (
            f"Ответ сервера не 200. Получен ответ {response.status_code}"
        )
        logger.error(message_response)
        raise exceptions.ResponseIsnt200Error(message_response)
    else:
        return response.json()


def check_response(response):
    """Проверяем ответ API."""
    try:
        timestamp = response["current_date"]
    except KeyError:
        logging.error(
            "Ключ current_date в ответе API Яндекс.Практикум отсутствует"
        )
    try:
        homeworks = response["homeworks"]
    except KeyError:
        message_api_key = "Ответ по ключу 'homeworks' пуст"
        logger.error(message_api_key)
        raise exceptions.APIKeyError(message_api_key)

    if isinstance(timestamp, int) and isinstance(homeworks, list):
        return homeworks
    else:
        raise TypeError("Неправильный формат ответа")


def parse_status(homework):
    """Получаем статус API для сообщения."""
    try:
        homework_name = homework["homework_name"]
    except homework_name is None:
        message_name = "Домашняя работа не найдена"
        logger.error(message_name)
        raise exceptions.HomeworksWasntFoundError(message_name)
    try:
        homework_status = homework["status"]
    except homework_status is None:
        message_status = "Статус домашней работы не найден"
        logger.error(message_status)
        raise exceptions.StatusUnknownError(message_status)
    try:
        verdict = HOMEWORK_VERDICTS[homework_status]
    except verdict is None:
        logger.error(
            "API домашки возвращает недокументированный статус домашней"
            "работы либо домашку без статуса"
        )

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    token_flag = True
    if (
        PRACTICUM_TOKEN is None
        or TELEGRAM_TOKEN is None
        or TELEGRAM_CHAT_ID is None
    ):
        token_flag = False
        logger.critical("Проверка токенов не пройдена")
        raise Exception("Проверка логов не пройдена")
    return token_flag


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()
    logger.info("Токены получены, бот запущен")
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            status = parse_status(homework[0])
            current_timestamp = response["current_date"]

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            send_message(bot, message)
            logger.error(f"Произошла ошибка: {error}")

        else:
            send_message(bot, status)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()

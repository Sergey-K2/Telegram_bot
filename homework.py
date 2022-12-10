"""Бот-ассистент Практикум."""
import logging
import os
import sys
import telegram
import time
import requests
import exceptions

from dotenv import load_dotenv


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

STATUS_CHANGE_MESSAGE = (
    'Изменился статус проверки работы "{homework_name}". {verdict}'
)

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
        logger.debug(f"Сообщение в Telegram отправлено: {message}")
    except telegram.TelegramError as error:
        logger.error(error, exc_info=True)


def get_api_answer(current_timestamp):
    """Делаем запрос к API."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={"from_date": current_timestamp},
        )
    except requests.exceptions.RequestException as exception:
        raise exception(
            f"Ошибка запроса. Параметры запроса: {ENDPOINT},"
            "{headers}, {params}."
        )

    if response.status_code != 200:
        raise exceptions.ResponseIsnt200Error(
            f"Ответ сервера не 200."
            f"Получен ответ {response.status_code}. Параметры запроса:"
            f"{ENDPOINT}, {HEADERS}, {current_timestamp}. Сообщение сервера:"
            f"{response.get('message')}"
        )
    return response.json()


def check_response(response):
    """Проверяем ответ API."""
    try:
        homeworks = response["homeworks"]
    except KeyError:
        raise KeyError("Нет ключа 'homeworks'")

    if isinstance(homeworks, list):
        return homeworks
    raise TypeError(
        f"По ключу 'homeworks' получен объект формата" f"{type(homeworks)}"
    )


def parse_status(homework):
    """Получаем статус API для сообщения."""
    try:
        homework_name = homework["homework_name"]
    except KeyError:
        raise KeyError("Нет проверенныъ домашних работ")
    try:
        status = homework["status"]
    except KeyError:
        raise KeyError("Статус домашней работы не найден")
    try:
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError:
        raise KeyError(f"Ошибка статуса. Получен статус{verdict}")

    return STATUS_CHANGE_MESSAGE.format(
        homework_name=homework_name, verdict=verdict
    )


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = {
        "practicum_token": PRACTICUM_TOKEN,
        "telegram_token": TELEGRAM_TOKEN,
        "telegram_chat_id": TELEGRAM_CHAT_ID,
    }
    token_flag = True
    for key, token in tokens.items():
        if token is None:
            logging.critical(f"Проверка токена {key} не пройдена")
            token_flag = False
    return token_flag


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit()
    logger.info("Токены получены, бот запущен")
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            status = parse_status(homeworks[0])
            send_message(bot, status)
            current_timestamp = response.get("current_date", int(time.time()))

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            send_message(bot, message)
            logger.error(message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()

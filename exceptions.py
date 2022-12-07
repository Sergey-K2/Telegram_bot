class ResponseIsnt200Error(Exception):
    """Сервер не возвращает 200 в ответ на запрос."""

    pass


class HomeworksWasntFoundError(Exception):
    """Домашних работ не найдено."""

    pass


class StatusUnknownError(Exception):
    """Статус домашней работы не известен."""

    pass


class APIKeyError(KeyError):
    """В ответе API нет ключа homeworks."""

    pass

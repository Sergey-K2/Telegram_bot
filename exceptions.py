class ResponseIsnt200Error(Exception):
    """Сервер не возвращает 200 в ответ на запрос."""

    pass

class RequestError(Exception):
    """Ошибка запроса."""

    pass



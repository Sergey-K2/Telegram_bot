class ResponseIsnt200Error(Exception):
    """Сервер не возвращает 200 в ответ на запрос."""

    pass


class SomethingWrongWithRequestError(Exception):
    """Ошибка запроса"""

    pass


class ResponseIsntDictionaryError(TypeError):
    """Ошибка запроса"""

    pass

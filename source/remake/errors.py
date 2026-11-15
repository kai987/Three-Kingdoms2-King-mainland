"""User-facing transactional command error."""
INVALID_SAVE_MESSAGE = '存档无效，当前进度未改变。'


class GameError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

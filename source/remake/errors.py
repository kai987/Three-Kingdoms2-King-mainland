"""User-facing transactional command error."""
class GameError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

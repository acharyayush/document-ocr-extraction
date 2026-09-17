class BaseUrlNotSetException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class IdentifierNotSetException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class PatchRequestFailedException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class ItemNotFoundException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
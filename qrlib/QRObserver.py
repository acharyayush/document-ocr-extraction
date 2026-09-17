from abc import ABC, abstractmethod


class QRSubscriber(ABC):

    @abstractmethod
    def notify(self, message) -> None:
        pass


class QRPublisher:

    def __init__(self):
        self._subscribers = set()

    def register(self, subscriber: QRSubscriber) -> None:
        self._subscribers.add(subscriber)

    def unregister(self, subscriber: QRSubscriber) -> None:
        self._subscribers.discard(subscriber)

    def notify(self, message) -> None:
        for subscriber in self._subscribers:
            subscriber.notify(message)

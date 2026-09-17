from qrlib.QRLogger import QRLogger
from qrlib.QRObserver import QRSubscriber, QRPublisher
from qrlib.QRProcess import QRProcess
from qrlib.QRRunItem import QRRunItem


class QRComponent(QRSubscriber):

    def __init__(self):
        self.run_item: QRRunItem = None
        self.logger: QRLogger = None

    def notify(self, run_item: QRRunItem):
        self.run_item = run_item
        self.logger = run_item.logger
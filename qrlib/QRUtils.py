from robot.libraries.BuiltIn import BuiltIn
from RPA.Browser.Selenium import Selenium
from RPA.Robocorp.Vault import Vault
from qrlib.QRVault import QRVault, CustomVault
from qrlib.QREnv import QREnv


def ltc(message: str) -> None:
    BuiltIn().log_to_console(f"\n{message}")


def display(msg, pp: bool = False) -> None:
    if QREnv.DEBUG:
        ltc(f"\n{msg}")
        if pp:
            print(msg)


def get_secret(name):
    if (QREnv.NO_PLATFORM):
        secret = Vault().get_secret(name)
    else:
        secret = CustomVault(identifier=QREnv.IDENTIFIER, URL=QREnv.BASE_URL).get_vault(name)
        # if(QREnv.PLATFORM_VERSION == 1):
        #     secret = CustomVault(identifier=QREnv.IDENTIFIER, URL=QREnv.BASE_URL).get_vault(name)
        # else:
        #     secret = QRVault().get_secret(name)
    if (not secret):
        raise Exception("Failed to load vault credentials")
    return secret
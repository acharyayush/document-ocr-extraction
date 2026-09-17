from robot.libraries.BuiltIn import BuiltIn
import os
import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


class _LaxSSLAdapter(HTTPAdapter):
    # ponytail: bypasses ASN.1 parse errors from corporate SSL inspection proxies
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        super().init_poolmanager(*args, **kwargs)


class QREnv:

    BOT_NAME = 'BotName'           # Name of the bot. Will be used in email notifications
    
    PLATFORM_VERSION = 2            # v1 currently in NCell, Prime, Civil, NMB. Rest are on v2     
    NO_PLATFORM = True
    
    IDENTIFIER = os.environ.get("identifier")                             # For platform v2
    
    VERIFY_SSL = False
    DEBUG = True
    
    BASE_DIR = os.environ.get("ROBOT_ROOT")                                     
    ARTIFACT_DIR = os.environ.get("ROBOT_ARTIFACTS")                           # Default to output directory
    DEFAULT_STORAGE_LOCATION = os.path.join(BASE_DIR, 'storage_downloads')     # Downloaded files from storage bucket will be stored here

    
    # ENVIRONMENTS - Should be retrieved dynamically from django env
    ENV_LOCAL = "LOCAL"             # Use for locahost
    ENV_QR_DEV = "QR_DEV"           # Use for internal dev server
    ENV_QR_UAT = "QR_UAT"           # Use for internal uat server
    ENV_UAT = "UAT"                 # Use for client uat server
    ENV_PRODUCTION = "PRODUCTION"   # Use for client production

    # Platform URLS
    URL_LOCAL = "http://127.0.0.1:8000/api/v1"                  # Use for locahost
    URL_QR_DEV_URL = ""                                          # Use for internal dev server
    URL_QR_UAT_URL = ""                                          # Use for internal uat server
    URL_UAT_URL = ""                                            # Use for client uat server
    URL_PROD = ""                                               # Use for client production

    # Dictiory to pick Platform URL based on current Environment
    ENV_URL = {
        ENV_LOCAL: URL_LOCAL,
        ENV_QR_DEV: URL_QR_DEV_URL,
        ENV_QR_UAT: URL_QR_UAT_URL,
        ENV_UAT: URL_UAT_URL,
        ENV_PRODUCTION: URL_PROD
    }

    ENVIRONMENT = os.environ.get("ENVIRONMENT", ENV_LOCAL)
    
    try:
        BASE_URL = ENV_URL[ENVIRONMENT]
    except Exception as e:
        BASE_URL = URL_LOCAL


    # Set required vaults, queues and storage buckets
    # Vault items are fetched. However, queues and storage buckets are only checked if they are accessible
    QUEUE_NAMES = []
    STORAGE_NAMES = []
    VAULT_NAMES = []

    # Retrieved vault items are set in this dictionary
    VAULTS = {}

    @staticmethod
    def session() -> requests.Session:
        s = requests.Session()
        s.mount('https://', _LaxSSLAdapter())
        return s


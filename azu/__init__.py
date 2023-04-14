import os
import logging
from dotenv import load_dotenv
from definitions import ROOT_DIR

load_dotenv(os.path.join(ROOT_DIR, "azu", ".env"))
assert "AZURE_SUBSCRIPTION_ID" in os.environ
logging.basicConfig(level="INFO")

from azu.main import *

"""Constants for the Delhaize integration."""

from datetime import timedelta

DOMAIN = "delhaize_ha"
NAME = "Delhaize"

API_URL = "https://www.delhaize.be/api/v1/"
BASE_URL = "https://www.delhaize.be"
DEFAULT_LANGUAGE = "nl"
UPDATE_INTERVAL = timedelta(hours=1)

CONF_AUTO_ACTIVATE_OFFERS = "auto_activate_offers"
CONF_COOKIE = "cookie"
CONF_LANGUAGE = "language"

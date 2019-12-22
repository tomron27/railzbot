import logging

# HTTP / Server params
WAKEUP_PERIOD = 600

# Railway API params
BASE_URL = "https://www.rail.co.il/apiinfo/api/Plan/GetRoutes"
ROUTE_LIMIT = 5

# Schedule params
DAYS_DICT = {'א': 6, 'ב': 0, 'ג': 1, 'ד': 2, 'ה': 3, 'ו': 4, 'ש': 5}
REV_DAYS_DICT = {v: k for k, v in DAYS_DICT.items()}

# Bot conversation params
CHOOSE_ORIGIN, CHOOSE_DEST, CHOOSE_TIME, PARSE_DAY, PARSE_HOUR, CUSTOM_DAY, PAST_ROUTE, TIME_SCHEDULE, DAY_SCHEDULE = range(9)

# Enabling logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

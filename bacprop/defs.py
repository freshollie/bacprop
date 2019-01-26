import logging


class Logable:
    _debug = logging.debug
    _info = logging.info
    _warning = logging.warning
    _error = logging.error
    _critical = logging.critical

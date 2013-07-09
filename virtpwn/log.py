import logging
import blessings


log_commands = False

INFO = logging.INFO
# between info and debug
VERBOSE = 15
DEBUG = logging.DEBUG

formatter = logging.Formatter(fmt='%(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log = logging.getLogger('virtpwn')
log.setLevel(logging.INFO)
log.addHandler(handler)

term = blessings.Terminal()


def warning(*args, **kwargs):
    log.warning(*args, **kwargs)

def info(*args, **kwargs):
    log.info(*args, **kwargs)

def verbose(*args, **kwargs):
    log.log(VERBOSE, *args, **kwargs)

def debug(*args, **kwargs):
    log.debug(*args, **kwargs)

def command(*args, **kwargs):
    if log_commands:
        log.info(*args, **kwargs)

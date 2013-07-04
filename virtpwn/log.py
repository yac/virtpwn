import logging
import blessings

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

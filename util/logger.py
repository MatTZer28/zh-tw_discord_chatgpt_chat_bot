import logging


class CustomFormatter(logging.Formatter):

    blue = "\033[94m"
    yellow = "\033[33m"
    red = "\033[91m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


logger = logging.getLogger('DISCORD_BOT')
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('log/logs.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(CustomFormatter())

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(CustomFormatter())

logger.addHandler(file_handler)
logger.addHandler(stream_handler)
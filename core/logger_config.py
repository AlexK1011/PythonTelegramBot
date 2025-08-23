import logging
import re
from logging.handlers import TimedRotatingFileHandler

import colorlog
import os


def setup_logger():
    """Настройка логирования с цветным выводом в консоль и записью в файл"""

    logger = logging.getLogger('telegram_bot')
    logger.setLevel(logging.DEBUG)

    logger.handlers.clear()

    file_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d:%(filename)s:%(levelname)s:%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s.%(msecs)03d:%(filename)s:%(levelname)s:%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )

    if not os.path.exists('logs'):
        os.makedirs('logs')

    file_handler = TimedRotatingFileHandler(
        'logs/telegram_bot.log',
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )

    file_handler.suffix = "%Y-%m-%d"
    file_handler.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()
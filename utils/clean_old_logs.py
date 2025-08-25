import asyncio
import os
import re
from datetime import datetime
from core.config import log_retention_days
from core.logger_config import logger


async def regular_cleaning():
    while True:
        try:
            await clean_old_logs()
            await asyncio.sleep(24 * 60 * 60)
        except Exception as e:
            logger.error(f"Ошибка при очистке логов: {e}")


async def clean_old_logs():
    """Очищает старые логи при запуске"""
    log_dir = 'logs'

    logger.info("=== НАЧАЛО ОЧИСТКИ ЛОГОВ ===")

    if not os.path.exists(log_dir):
        logger.error(f"Папка {log_dir} не существует!")
        return

    all_files = os.listdir(log_dir)

    now = datetime.now()

    pattern = re.compile(r'telegram_bot\.log\.(\d{4}-\d{2}-\d{2})')

    deleted_count = 0
    processed_count = 0

    for filename in all_files:

        match = pattern.match(filename)
        if match:
            date_str = match.group(1)

            try:
                file_date = datetime.strptime(date_str, '%Y-%m-%d')
                days_old = (now - file_date).days

                if days_old > log_retention_days:
                    file_path = os.path.join(log_dir, filename)

                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"  - Файл {filename} успешно удален!")

                    except OSError as e:
                        logger.error(f"  - ОШИБКА при удалении файла {filename}: {e}")
                        logger.error(f"  - Тип ошибки: {type(e).__name__}")

                        if os.path.exists(file_path):
                            logger.error(f"  - Файл все еще существует после попытки удаления")
                        else:
                            logger.info(f"  - Файл успешно удален")

            except ValueError as e:
                logger.error(f"  - ОШИБКА парсинга даты '{date_str}': {e}")
                continue
        else:
            logger.info(f"  - Файл не подходит под паттерн логов")

        processed_count += 1

    logger.info(f"=== ОЧИСТКА ЗАВЕРШЕНА ===")
    logger.info(f"Обработано файлов: {processed_count}")
    logger.info(f"Удалено файлов: {deleted_count}")

    remaining_files = os.listdir(log_dir)
    logger.info(f"Осталось файлов в папке: {len(remaining_files)}")
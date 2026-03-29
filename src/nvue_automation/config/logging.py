import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """
    攔截標準 logging 日誌並轉發到 loguru
    """

    def emit(self, record: logging.LogRecord) -> None:
        # 獲取對應的 Loguru 級別
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 查找調用者的堆棧幀，跳過 logging 模塊的內部調用
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging():
    """
    配置 logging，將所有日誌轉發至 loguru
    """
    # 移除 loguru 的默認 handler
    logger.remove()

    # 新增自定義的 handler，
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG",
        colorize=True,
    )

    logger.add(
        "logs/app_{time}_error.log",
        rotation="100 MB",
        retention="10 days",
        compression="zip",
        level="ERROR",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    # 攔截 uvicorn 和其他使用標準 logging 的庫的日誌
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.INFO)

    for logger_name in (
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "asyncio",
        "starlette",
    ):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = []
        logging_logger.propagate = True

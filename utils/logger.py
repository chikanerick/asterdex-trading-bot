from colorama import init, Fore, Style
import logging
from datetime import datetime

init(autoreset=True)

SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")

def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, message, args, **kwargs)

logging.Logger.success = success

class ColorFormatter(logging.Formatter):
    def format(self, record):

        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname

        if level == "INFO":
            prefix = Fore.CYAN + f"[{timestamp}] [INFO]" + Style.RESET_ALL
        elif level == "WARNING":
            prefix = Fore.YELLOW + f"[{timestamp}] [WARNING]" + Style.RESET_ALL
        elif level == "ERROR":
            prefix = Fore.RED + f"[{timestamp}] [ERROR]" + Style.RESET_ALL
        elif level == "SUCCESS":
            prefix = Fore.GREEN + f"[{timestamp}] [SUCCESS]" + Style.RESET_ALL
        else:
            prefix = f"[{timestamp}] [{level}]"

        return f"{prefix} {record.getMessage()}"


logger = logging.getLogger("AsterDex")
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

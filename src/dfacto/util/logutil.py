import logging
import logging.handlers
import multiprocessing as mp
import time
from pathlib import Path
from queue import Empty
from typing import Union, Optional

from dfacto.util.basicpatterns import Singleton


class _LogServer(mp.Process):
    def __init__(
        self,
        log_queue: mp.Queue,  # type: ignore
        log_file: Path,
        log_level: int = logging.INFO,
        log_on_console: bool = True,
    ):
        super().__init__()

        self.name = "LogServer"
        self.log_queue = log_queue
        self.log_file = log_file
        self.log_level = log_level
        self.log_on_consolde = log_on_console

    def configure(self) -> None:
        logging_format = "%(processName)-15s%(levelname)s: %(message)s"
        logging_date_format = "%Y-%m-%d %H:%M:%S"
        # file_logging_format = '%(asctime)s.%(msecs)03d %(levelname)-8s %(processName)-15s %(name)s %(filename)s %(lineno)d: %(message)s'
        file_logging_format = "%(asctime)s.%(msecs)03d %(levelname)-8s %(processName)-15s %(threadName)-20s %(message)s"
        console_log_level = logging.WARNING

        root = logging.getLogger()
        try:
            file_handler = logging.FileHandler(self.log_file, mode="w")
        except OSError:
            console_log_level = self.log_level
        else:
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(
                logging.Formatter(file_logging_format, logging_date_format)
            )
            # file_handler.setFormatter(logging.Formatter(file_logging_format))
            root.addHandler(file_handler)
        finally:
            if self.log_on_consolde:
                console_handler = logging.StreamHandler()
                console_handler.set_name("console")
                console_handler.setFormatter(logging.Formatter(logging_format))
                console_handler.setLevel(console_log_level)
                root.addHandler(console_handler)

            root.setLevel(logging.DEBUG)

    def run(self) -> None:
        self.configure()
        while True:
            try:
                try:
                    record = self.log_queue.get(block=True, timeout=0.01)
                except Empty:
                    continue
                if (
                    record is None
                ):  # We send this as a sentinel to tell the listener to quit.
                    print("Stopping LogServer...")
                    break
                logger = logging.getLogger(record.name)
                logger.handle(record)
            except Exception:
                import sys
                import traceback

                print("Whoops! Problem:", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)


class LogConfig(metaclass=Singleton):
    def __init__(
        self,
        log_file: Optional[Path] = None,
        log_level: int = logging.INFO,
        log_on_console: bool = True,
    ):
        self.log_file = log_file or Path(".")
        self.log_level = log_level
        self.log_on_console = log_on_console

        logging.captureWarnings(True)

        self.log_queue = mp.Queue(maxsize=-1)  # type: ignore
        self.log_server = _LogServer(
            self.log_queue, self.log_file, self.log_level, self.log_on_console
        )

    def init_logging(self) -> None:
        self.log_server.start()
        configure_root_logger(self.log_queue, self.log_level)

    def stop_logging(self) -> None:
        time.sleep(1)
        self.log_queue.put_nowait(None)
        self.log_server.join()
        print("LogServer stopped")


def configure_root_logger(
    log_queue: mp.Queue, log_level: Union[int, str]  # type: ignore
) -> None:
    handler = logging.handlers.QueueHandler(log_queue)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(log_level)

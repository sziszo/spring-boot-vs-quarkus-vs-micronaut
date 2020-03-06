import docker
import time
import re
import logging.config

from docker.errors import NotFound
from utils import bytesto

logging.config.fileConfig(fname='log.conf', disable_existing_loggers=False)
LOGGER = logging.getLogger(__name__)


class AppMonitor:

    def __init__(self, waiting_message, timeout):
        self.message = waiting_message
        self.timeout = timeout

    def run(self, image_name, port):
        self.__stop_container(image_name)

        container = self.__start_container(image_name, port)
        self.__monitor_startup(container)

        LOGGER.info(f'{image_name} listening on port {port}')
        self.print_startup_result()
        self.print_memory_usage(container)

    @staticmethod
    def __stop_container(container_name):
        client = docker.from_env()
        try:
            container = client.containers.get(container_name)
            LOGGER.warning(f'{container_name} container is running')
            container.stop()
            LOGGER.info(f'{container_name} container is stopped')
        except NotFound:
            LOGGER.debug(f'{container_name} is not running')

    @staticmethod
    def __start_container(image_name, port):
        LOGGER.info(f'Starting {image_name} container ...')
        client = docker.from_env()
        return client.containers.run(image_name,
                                     name=f'{image_name}',
                                     detach=True,
                                     remove=True,
                                     network='todo_app_network',
                                     ports={f'{port}/tcp': port},
                                     environment=["POSTGRES_DB_HOST=infra-db"])

    def __monitor_startup(self, container):
        start_time = time.time()
        end_time = start_time
        for line in container.logs(stream=True):
            log_message = str(line, 'utf-8')
            if self.message in log_message:
                end_time = time.time()
                self.process_log_message(log_message)
                break
            elif end_time - start_time >= self.timeout:
                break

        self.startupTime = round(end_time - start_time, 3)

    def process_log_message(self, log_message):
        pass

    def print_startup_result(self):
        LOGGER.info(f'startupTime: {self.startupTime}')

    def run_test(self):
        pass

    @staticmethod
    def print_memory_usage(container):
        stats = container.stats(stream=False)
        LOGGER.info(f'memory usage: {round(bytesto(stats["memory_stats"]["usage"]), 1)}Mb')


class SpringAppMonitor(AppMonitor):
    APP_STARTUP_PATTERN = re.compile(r'in ([0-9]+[.]?[0-9]*) seconds')
    JVM_STARTUP_PATTERN = re.compile(r'for ([0-9]+[.]?[0-9]*)')

    LOGGER = logging.getLogger(__name__)

    def __init__(self, timeout=120):
        super().__init__('Started', timeout)
        self.app_startup = ''
        self.jvm_startup = ''

    def process_log_message(self, log_message):
        self.app_startup = re.search(self.APP_STARTUP_PATTERN, log_message).group(1)
        self.jvm_startup = re.search(self.JVM_STARTUP_PATTERN, log_message).group(1)

    def print_startup_result(self):
        # super().printStartupResult()
        LOGGER.info(f'app-startup: {self.app_startup}')
        LOGGER.info(f'jvm-startup: {self.jvm_startup}')


class QuarkusAppMonitor(AppMonitor):
    LOGGER = logging.getLogger(__name__)

    APP_STARTUP_PATTERN = re.compile(r'in ([0-9]+[.]?[0-9]*)s')

    def __init__(self, timeout=120):
        super().__init__('started in', timeout)
        self.app_startup = ''
        self.jvm_startup = ''

    def process_log_message(self, log_message):
        self.app_startup = re.search(self.APP_STARTUP_PATTERN, log_message).group(1)

    def print_startup_result(self):
        # super().printStartupResult()
        LOGGER.info(f'app-startup: {self.app_startup}')
        LOGGER.info(f'jvm-startup: {self.startupTime}')

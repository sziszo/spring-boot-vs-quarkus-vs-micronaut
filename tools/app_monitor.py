import logging.config
import re
import time
from collections import defaultdict

import docker
from docker.errors import NotFound

from .app_utils import bytesto

LOGGER = logging.getLogger(__name__)


class AppMonitor:

    def __init__(self, waiting_message, timeout):
        self.message = waiting_message
        self.timeout = timeout
        self.startupTime = 0
        self.startupMemoryUsage = 0

    def start(self):
        pass

    def stop(self):
        pass

    def run(self, image_name, container_port, host_port=None):
        self.stop_container(image_name)

        port = host_port if host_port else container_port
        container = self.__start_container(image_name, container_port, port)
        self.__monitor_startup(container)
        self.__monitor_startup_memory_usage(container)

        LOGGER.info(f'{image_name} listening on port {port}')
        self.print_startup_result()
        self.print_memory_usage(container)

    @staticmethod
    def stop_container(container_name):
        client = docker.from_env()
        try:
            container = client.containers.get(container_name)
            LOGGER.warning(f'{container_name} container is running')
            container.stop()
            LOGGER.info(f'{container_name} container is stopped')
        except NotFound:
            LOGGER.debug(f'{container_name} is not running')

    @staticmethod
    def __start_container(image_name, container_port, host_port):
        LOGGER.info(f'Starting {image_name} container ...')
        client = docker.from_env()
        return client.containers.run(image_name,
                                     name=f'{image_name}',
                                     detach=True,
                                     remove=True,
                                     network='todo_app_network',
                                     ports={f'{container_port}/tcp': host_port},
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

    def __monitor_startup_memory_usage(self, container):
        stats = container.stats(stream=False)
        self.startupMemoryUsage = round(bytesto(stats["memory_stats"]["usage"]), 1)

    def print_startup_result(self):
        LOGGER.info(f'startupTime: {self.startupTime}')

    def run_test(self):
        pass

    def print_memory_usage(self, container):
        LOGGER.info(f'memory usage: {self.startupMemoryUsage}Mb')

    @staticmethod
    def to_result_table(app_name, app_startup, jvm_startup, startup_memory_usage):
        table = defaultdict(dict)
        table[app_name]["app-startup"] = app_startup
        table[app_name]["jvm-startup"] = jvm_startup
        table[app_name]["startup-memory-usage"] = f'{startup_memory_usage}Mb'
        return table


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
        LOGGER.info(f'vm-startup: {self.jvm_startup}')

    def get_result_table(self, app_name):
        return super().to_result_table(app_name, self.app_startup, self.jvm_startup, self.startupMemoryUsage)


class QuarkusAppMonitor(AppMonitor):
    LOGGER = logging.getLogger(__name__)

    APP_STARTUP_PATTERN = re.compile(r'in ([0-9]+[.]?[0-9]*)s')

    def __init__(self, timeout=120):
        super().__init__('started in', timeout)
        self.app_startup = ''

    def process_log_message(self, log_message):
        self.app_startup = re.search(self.APP_STARTUP_PATTERN, log_message).group(1)

    def print_startup_result(self):
        # super().printStartupResult()
        LOGGER.info(f'app-startup: {self.app_startup}')
        LOGGER.info(f'jvm-startup: {self.startupTime}')

    def get_result_table(self, app_name):
        return super().to_result_table(app_name, self.app_startup, self.startupTime, self.startupMemoryUsage)

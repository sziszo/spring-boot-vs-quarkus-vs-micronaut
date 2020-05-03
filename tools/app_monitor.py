import logging.config
import re
import time
from collections import defaultdict

from .platform import PlatformManagerFactory

LOGGER = logging.getLogger(__name__)


def set_verbose():
    LOGGER.setLevel('DEBUG')


class AppMonitor:

    def __init__(self, platform_manager, waiting_message, timeout):
        self.platformManager = platform_manager
        self.message = waiting_message
        self.timeout = timeout
        self.startupTime = 0
        self.startupMemoryUsage = 0

    def start(self):
        pass

    def stop(self):
        pass

    def run(self):
        self.platformManager.stop_app()
        self.platformManager.start_app()
        self.__monitor_startup()

        LOGGER.info(f'{self.platformManager.container_name} listening on port {self.platformManager.host_port}')

        self.__monitor_startup_memory_usage()

        self.print_startup_result()
        self.print_memory_usage()

    def __monitor_startup(self):
        start_time = time.time()
        end_time = start_time
        attempt = 1
        done = False
        while not done and attempt < 10:
            for line in self.platformManager.logs():
                log_message = str(line, 'utf-8')
                LOGGER.debug(f'line={log_message}')
                if self.message in log_message:
                    end_time = time.time()
                    self.process_log_message(log_message)
                    done = True
                    break
                elif time.time() - start_time >= self.timeout:
                    done = True
                    break
            attempt += 1
            if not done:
                sleeping_time = 1
                LOGGER.info(f'attempt {attempt}: waiting {sleeping_time} to get the logs of {self.platformManager.container_name}')
                time.sleep(sleeping_time)

        self.startupTime = round(end_time - start_time, 3)

    def process_log_message(self, log_message):
        pass

    def run_test(self):
        pass

    def print_startup_result(self):
        LOGGER.info(f'startupTime: {self.startupTime}')

    def __monitor_startup_memory_usage(self):
        self.startupMemoryUsage = self.platformManager.memory_usage()

    def print_memory_usage(self):
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

    def __init__(self, image_name, container_name, container_port, platform='docker', timeout=120):
        super().__init__(PlatformManagerFactory.create(platform, image_name, container_name, container_port),
                         'Started', timeout)
        self.image_name = image_name
        self.container_name = container_name
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

    def __init__(self, image_name, container_name, container_port, host_port, platform='docker', timeout=120):
        super().__init__(PlatformManagerFactory.create(platform, image_name, container_name, container_port, host_port),
                         'started in', timeout)
        self.image_name = image_name
        self.container_name = container_name
        self.app_startup = ''

    def process_log_message(self, log_message):
        self.app_startup = re.search(self.APP_STARTUP_PATTERN, log_message).group(1)

    def print_startup_result(self):
        # super().printStartupResult()
        LOGGER.info(f'app-startup: {self.app_startup}')
        LOGGER.info(f'jvm-startup: {self.startupTime}')

    def get_result_table(self, app_name):
        return super().to_result_table(app_name, self.app_startup, self.startupTime, self.startupMemoryUsage)

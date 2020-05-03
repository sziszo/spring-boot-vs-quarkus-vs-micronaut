#!/usr/bin/env python3
import argparse

import pandas as pd
import yaml

from tools.app_monitor import SpringAppMonitor, QuarkusAppMonitor, set_verbose as set_verbose_app_monitor
from tools.platform import set_verbose as set_verbose_platform


def set_verbose():
    set_verbose_platform()
    set_verbose_app_monitor()


class SpringTodoAppMonitor(SpringAppMonitor):

    def __init__(self, platform='docker'):
        name = 'spring-todo-app'
        super().__init__(image_name=f'{name}:latest', container_name=name, container_port=8090, platform=platform)

    def start(self):
        super().run()
        return self.get_result_table(self.container_name)

    def stop(self):
        self.platformManager.stop_app()


class QuarkusTodoAppMonitor(QuarkusAppMonitor):

    def __init__(self, build_type='jvm', platform='docker'):
        port = 8091 if build_type == 'jvm' else 8092
        name = f'quarkus-todo-app-{build_type}'
        super().__init__(image_name=f'{name}:latest', container_name=name, container_port=8091, host_port=port,
                         platform=platform)
        self.build_type = build_type

    def start(self):
        super().run()
        return super().get_result_table(self.container_name)

    def stop(self):
        self.platformManager.stop_app()


class MonitorApp:
    def __init__(self, build_type='jvm', app_type='all', platform='docker'):
        self.type = app_type
        self.build_type = build_type
        self.platform = platform

    def monitor(self, action_command='start'):
        monitors = []
        if self.type != 'spring' and (self.build_type == 'all' or self.build_type == 'native'):
            monitors.append(QuarkusTodoAppMonitor('native', self.platform))
        if self.build_type == 'all' or self.build_type == 'jvm':
            if self.type == 'all' or self.type == 'spring':
                monitors.append(SpringTodoAppMonitor(platform=self.platform))
            if self.type == 'all' or self.type == 'quarkus':
                monitors.append(QuarkusTodoAppMonitor('jvm', self.platform))

        is_start = action_command == 'start'
        result = {}
        for monitor in monitors:
            result.update(monitor.start()) if is_start else monitor.stop()

        return result


def main():
    parser = argparse.ArgumentParser(description='Manage the infrastructure',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-t", "--type", help="set app type", default='all', choices=['spring', 'quarkus', 'all'])
    parser.add_argument("-b", "--build_type", help="set build type", default='all', choices=['jvm', 'native', 'all'])
    parser.add_argument("-p", "--platform", help="set platform type", default='docker', choices=['docker', 'k8s'])
    parser.add_argument("-v", "--verbose", help="set verbose", default=False, type=bool)
    parser.add_argument("action_command", help="set action command", default='start', choices=['start', 'stop'],
                        nargs='?')
    args = parser.parse_args()

    import logging.config
    with open('app_log.yml', 'r') as f:
        log_cfg = yaml.safe_load(f.read())
        logging.config.dictConfig(log_cfg)

    if args.verbose:
        set_verbose()

    m = MonitorApp(args.build_type, args.type, args.platform)
    result = m.monitor(args.action_command)
    if result:
        print(f'{pd.DataFrame(result)}')


if __name__ == '__main__':
    main()

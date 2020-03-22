#!/usr/bin/env python3
import argparse
import logging.config

import pandas as pd
import yaml

from tools.app_monitor import SpringAppMonitor, QuarkusAppMonitor


class SpringTodoAppMonitor(SpringAppMonitor):

    def __init__(self):
        super().__init__()
        self.image_name = 'spring-todo-app'

    def start(self):
        super().run(image_name=self.image_name, container_port=8090)
        return super().get_result_table(self.image_name)

    def stop(self):
        super().stop_container(self.image_name)


class QuarkusTodoAppMonitor(QuarkusAppMonitor):

    def __init__(self, build_type='jvm'):
        super().__init__()
        self.build_type = build_type
        self.image_name = f'quarkus-todo-app-{self.build_type}'

    def start(self):
        port = 8091 if self.build_type == 'jvm' else 8092
        super().run(image_name=self.image_name, container_port=8091, host_port=port)
        return super().get_result_table(self.image_name)

    def stop(self):
        super().stop_container(self.image_name)
        return super().get_result_table(self.image_name)


class MonitorApp:
    def __init__(self, build_type='jvm', app_type=None):
        self.type = app_type
        self.build_type = build_type

    def monitor(self, action_command='start'):
        with open('app_log.yml', 'r') as f:
            log_cfg = yaml.safe_load(f.read())
            logging.config.dictConfig(log_cfg)

        monitors = []
        if self.build_type == 'native':
            monitors.append(QuarkusTodoAppMonitor(self.build_type))
        else:
            if not self.type or self.type == 'spring':
                monitors.append(SpringTodoAppMonitor())
            if not self.type or self.type == 'quarkus':
                monitors.append(QuarkusTodoAppMonitor(self.build_type))

        is_start = action_command == 'start'
        result = {}
        for monitor in monitors:
            result.update(monitor.start()) if is_start else monitor.stop()

        return result


def main():
    parser = argparse.ArgumentParser(description='Manage the infrastructure')
    parser.add_argument("-t", "--type", help="set app type", default='', choices=['spring', 'quarkus'])
    parser.add_argument("-b", "--build_type", help="set build type", default='jvm', choices=['jvm', 'native'])
    parser.add_argument("action_command", help="set action command", default='start', choices=['start', 'stop'],
                        nargs='?')
    args = parser.parse_args()

    m = MonitorApp(args.build_type, args.type)
    result = m.monitor(args.action_command)
    if result:
        print(f'{pd.DataFrame(result)}')


if __name__ == '__main__':
    main()

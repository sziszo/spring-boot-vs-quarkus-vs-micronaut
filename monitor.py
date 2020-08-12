#!/usr/bin/env python3
import json

import argparse
import pandas as pd
import yaml

from tools.app_monitor import SpringAppMonitor, QuarkusAppMonitor, GeneralAppMonitor, \
    set_verbose as set_verbose_app_monitor
from tools.platform import set_verbose as set_verbose_platform


def set_verbose():
    set_verbose_platform()
    set_verbose_app_monitor()


class MonitorFactory:

    @staticmethod
    def create_spring_todo_app_monitor(platform='docker'):
        return MonitorFactory.create(app_type='spring', build_type='jvm', platform=platform,
                                     app_desc={'name': 'spring-todo-app', 'container_port': 8090})

    @staticmethod
    def create_quarkus_todo_app_monitor(build_type='jvm', platform='docker'):
        port = 8091 if build_type == 'jvm' else 8092
        return MonitorFactory.create(app_type='quarkus', build_type=build_type, platform=platform,
                                     app_desc={'name': 'quarkus-todo-app', 'container_port': 8091,
                                               'host_port': port})

    @staticmethod
    def create(app_type, build_type='jvm', platform='docker', app_desc={}):
        container_name = f'{app_desc["name"]}-{build_type}'
        image_name = f'{container_name}:latest'
        container_port = app_desc['container_port']
        host_port = app_desc.get('host_port', container_port)

        return {
            'spring': SpringAppMonitor(image_name, container_name, container_port, platform),
            'quarkus': QuarkusAppMonitor(image_name, container_name, container_port, host_port, platform),
            'general': GeneralAppMonitor(image_name, container_name, container_port, host_port, platform)
        }[app_type]


class MonitorApp:
    def __init__(self, build_type='jvm', app_type='all', platform='docker', app_descriptors=[]):
        self.type = app_type
        self.build_type = build_type
        self.platform = platform
        self.app_descriptors = app_descriptors

    def monitor(self, action_command='start'):
        monitors = []
        if self.app_descriptors:
            for app_desc in self.app_descriptors:
                app_type = self.type if self.type != 'all' else app_desc['app_type']
                build_type = self.build_type if self.build_type != 'all' else app_desc['build_type']
                monitors.append(MonitorFactory.create(app_type, build_type, self.platform, app_desc))
        else:
            if self.type != 'spring' and (self.build_type == 'all' or self.build_type == 'native'):
                monitors.append(MonitorFactory.create_quarkus_todo_app_monitor('native', self.platform))
            if self.build_type == 'all' or self.build_type == 'jvm':
                if self.type == 'all' or self.type == 'spring':
                    monitors.append(MonitorFactory.create_spring_todo_app_monitor(self.platform))
                if self.type == 'all' or self.type == 'quarkus':
                    monitors.append(MonitorFactory.create_quarkus_todo_app_monitor('jvm', self.platform))

        is_start = action_command == 'start'
        result = {}
        for monitor in monitors:
            result.update(monitor.start()) if is_start else monitor.stop()

        return result


def main():
    parser = argparse.ArgumentParser(description='Manage the infrastructure',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-t", "--type", help="set app type", default='all',
                        choices=['spring', 'quarkus', 'all', 'general'])
    parser.add_argument("-b", "--build_type", help="set build type", default='all', choices=['jvm', 'native', 'all'])
    parser.add_argument("-p", "--platform", help="set platform type", default='docker', choices=['docker', 'k8s'])
    parser.add_argument("-v", "--verbose", help="set verbose", default=False, type=bool)
    parser.add_argument("-d", "--app_desc", help="set app description file", type=str)
    parser.add_argument("action_command", help="set action command", default='start', choices=['start', 'stop'],
                        nargs='?')
    args = parser.parse_args()

    import logging.config
    with open('log.yml', 'r') as f:
        log_cfg = yaml.safe_load(f.read())
        logging.config.dictConfig(log_cfg)

    if args.verbose:
        set_verbose()

    app_descriptors = []
    if args.app_desc:
        with open(args.app_desc, 'r') as f:
            app_descriptors = json.loads(f.read())

    m = MonitorApp(args.build_type, args.type, args.platform, app_descriptors)
    result = m.monitor(args.action_command)
    if result:
        print(f'{pd.DataFrame(result)}')


if __name__ == '__main__':
    main()

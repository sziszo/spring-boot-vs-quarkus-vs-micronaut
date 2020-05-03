#!/usr/bin/env python3
import argparse
import logging.config
import subprocess

import pandas as pd
import yaml

from app_build import BuilderApp, set_verbose as set_verbose_builder
from app_monitor import MonitorApp, set_verbose as set_verbose_monitor
from tools.app_utils import merge_dicts


def set_verbose():
    set_verbose_monitor()
    set_verbose_builder()


def start_infra(platform):
    subprocess.run(['./infra.py', '-p', f'{platform}', 'start'], check=True)


def build_and_run_apps(build_type='jvm', app_type='all', platform='docker'):
    b = BuilderApp(build_type, app_type)
    build_result = b.build()

    m = MonitorApp(build_type, app_type, platform)
    m.monitor('stop')
    monitor_result = m.monitor('start')

    return merge_dicts(build_result, monitor_result)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-t", "--type", help="set app type", default='all', choices=['spring', 'quarkus', 'all'])
    parser.add_argument("-p", "--platform", help="set platform type", default='docker', choices=['docker', 'k8s'])
    parser.add_argument("-v", "--verbose", help="set verbose", default=False, type=bool)
    parser.add_argument("build_type", help="set build type", default='all', choices=['jvm', 'native', 'all'], nargs='?')
    args = parser.parse_args()

    with open('app_log.yml', 'r') as f:
        log_cfg = yaml.safe_load(f.read())
        logging.config.dictConfig(log_cfg)

    if args.verbose:
        set_verbose()

    start_infra(args.platform)

    jvm_result = {}
    if args.build_type == 'all' or args.build_type == 'jvm':
        jvm_result = build_and_run_apps('jvm', args.type, args.platform)
        if jvm_result:
            print(f'JVM result:\n{pd.DataFrame(jvm_result)}\n')

    native_result = {}

    if args.type != 'spring' and (args.build_type == 'all' or args.build_type == 'native'):
        native_result = build_and_run_apps(build_type='native', platform=args.platform)
        if native_result:
            print(f'GraalVM result:\n{pd.DataFrame(native_result)}\n')

    if jvm_result and native_result:
        result = {}
        result.update(jvm_result)
        result.update(native_result)

        if result:
            print(f'Overall result:\n{pd.DataFrame(result)}\n')


if __name__ == '__main__':
    main()

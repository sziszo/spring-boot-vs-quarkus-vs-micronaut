#!/usr/bin/env python3
import argparse
import subprocess

import pandas as pd

from app_build import BuilderApp
from app_monitor import MonitorApp
from tools.app_utils import merge_dicts


def start_infra():
    subprocess.run(['infra/infra.py', 'start'], check=True)


def build_and_run_apps(build_type='jvm', app_type=None):
    b = BuilderApp(build_type, app_type)
    build_result = b.build()

    m = MonitorApp(build_type, app_type)
    m.monitor('stop')
    monitor_result = m.monitor('start')

    return merge_dicts(build_result, monitor_result)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-t", "--type", help="set app type", default='all', choices=['spring', 'quarkus', 'all'])
    parser.add_argument("build_type", help="set build type", default='all', choices=['jvm', 'native', 'all'], nargs='?')
    args = parser.parse_args()

    start_infra()

    jvm_result = {}
    if args.build_type == 'all' or args.build_type == 'jvm':
        jvm_result = build_and_run_apps('jvm', args.type)
        if jvm_result:
            print(f'JVM result:\n{pd.DataFrame(jvm_result)}\n')

    native_result = {}

    if args.type != 'spring' and (args.build_type == 'all' or args.build_type == 'native'):
        native_result = build_and_run_apps('native')
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

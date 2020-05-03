#!/usr/bin/env python3
import argparse
import logging.config

import pandas as pd
import yaml

from tools.app_builder import SpringAppBuilder, QuarkusAppBuilder, set_verbose as set_verbose_app_builder


def set_verbose():
    set_verbose_app_builder()


class SpringTodoAppBuilder(SpringAppBuilder):
    def __init__(self):
        super(SpringTodoAppBuilder, self).__init__('todo-app/spring-todo-app')


class QuarkusTodoAppBuilder(QuarkusAppBuilder):
    def __init__(self, build_type='jvm'):
        super(QuarkusTodoAppBuilder, self).__init__('todo-app/quarkus-todo-app', build_type)


class BuilderApp:
    def __init__(self, build_type='jvm', app_type='all'):
        self.build_type = build_type
        self.type = app_type

    def build(self):
        builders = []
        if self.build_type == 'native':
            builders = [QuarkusTodoAppBuilder(self.build_type)]
        else:
            if self.type == 'all' or self.type == 'spring':
                builders.append(SpringTodoAppBuilder())
            if self.type == 'all' or self.type == 'quarkus':
                builders.append(QuarkusTodoAppBuilder(self.build_type))

        result = {}
        for builder in builders:
            result.update(builder.build())
        return result


def main():
    parser = argparse.ArgumentParser(description='This is the builder for todo-app',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-t", "--type", help="set app type", default='all', choices=['spring', 'quarkus', 'all'])
    parser.add_argument("-v", "--verbose", help="set verbose", default=False, type=bool)
    parser.add_argument("build_type", help="set build type", default='all', choices=['jvm', 'native', 'all'], nargs='?')
    args = parser.parse_args()

    with open('log.yml', 'r') as f:
        log_cfg = yaml.safe_load(f.read())
        logging.config.dictConfig(log_cfg)

    if args.verbose:
        set_verbose()

    b = BuilderApp(args.build_type, args.type)
    result = b.build()
    if result:
        print(f'result:')
        print(f'{pd.DataFrame(result)}')


if __name__ == '__main__':
    main()

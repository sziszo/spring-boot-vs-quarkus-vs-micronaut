#!/usr/bin/env python3
import argparse
import logging.config

import pandas as pd
import yaml

from tools.app_builder import SpringAppBuilder, QuarkusAppBuilder


class SpringTodoAppBuilder(SpringAppBuilder):
    def __init__(self):
        super(SpringTodoAppBuilder, self).__init__('todo-app/spring-todo-app')


class QuarkusTodoAppBuilder(QuarkusAppBuilder):
    def __init__(self, build_type='jvm'):
        super(QuarkusTodoAppBuilder, self).__init__('todo-app/quarkus-todo-app', build_type)


class BuilderApp:
    def __init__(self, build_type='jvm', app_type=None):
        self.build_type = build_type
        self.type = app_type

    def build(self):
        with open('app_log.yml', 'r') as f:
            log_cfg = yaml.safe_load(f.read())
            logging.config.dictConfig(log_cfg)

        builders = []
        if self.build_type == 'native':
            builders = [QuarkusTodoAppBuilder(self.build_type)]
        else:
            if not self.type or self.type == 'spring':
                builders.append(SpringTodoAppBuilder())
            if not self.type or self.type == 'quarkus':
                builders.append(QuarkusTodoAppBuilder(self.build_type))

        result = {}
        for builder in builders:
            result.update(builder.build())
        return result


def main():
    parser = argparse.ArgumentParser(description='This is the builder for todo-app')
    parser.add_argument("-t", "--type", help="set app type", default=None, choices=['spring', 'quarkus'])
    parser.add_argument("build_type", help="set build type", default='jvm', choices=['jvm', 'native'], nargs='?')
    args = parser.parse_args()

    b = BuilderApp(args.build_type, args.type)
    result = b.build()
    if result:
        print(f'result:')
        print(f'{pd.DataFrame(result)}')


if __name__ == '__main__':
    main()

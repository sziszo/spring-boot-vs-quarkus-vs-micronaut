#!/usr/bin/env python3

import time
from app_monitor import SpringAppMonitor, QuarkusAppMonitor


class SpringTodoAppMonitor(SpringAppMonitor):

    def start(self):
        super().run(image_name='spring-todo-app', port=8090)


class QuarkusTodoAppMonitor(QuarkusAppMonitor):

    def __init__(self, build_type='jvm'):
        super().__init__()
        self.build_type = build_type

    def start(self):
        super().run(image_name=f'quarkus-todo-app-{self.build_type}', port=8091)


def main():
    monitors = [SpringTodoAppMonitor(), QuarkusTodoAppMonitor()]
    # monitors = [QuarkusTodoAppMonitor()]
    for monitor in monitors:
        monitor.start()
        time.sleep(5)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path

import docker
from docker.errors import NotFound

ENV_FILE = '.env'
TODO_APP_NETWORK = 'todo_app_network'
DEFAULT_LOG_FOLDER = '.logs'
SCRIPT_DIR = Path(__file__).parent.resolve()


def setup():
    print(f'creating {DEFAULT_LOG_FOLDER} folder')
    Path(DEFAULT_LOG_FOLDER).mkdir(exist_ok=True)

    print(f'checking {ENV_FILE} file... ', end='')
    if not Path(ENV_FILE).is_file():
        print('failed!')
        db_user = input("Enter db USERNAME [admin]: ") or "admin"
        db_pass = input("Enter db PASSWORD [admin]: ") or "admin"
        f = open(ENV_FILE, "w+")
        f.write(f'DB_USER={db_user}\nDB_PASSWORD={db_pass}\n')
    else:
        print('ok!')
    client = docker.from_env()

    try:
        print('checking network settings... ', end='')
        client.networks.get(TODO_APP_NETWORK)
        print('ok!')
    except NotFound:
        print('failed!')
        print("creating network for todo-apps", end='')
        client.networks.create(TODO_APP_NETWORK)
        print('done!')

    print('setup is finished')


def start():
    setup()
    subprocess.run(['docker-compose', '-f', f'{SCRIPT_DIR}/docker-compose.yml', 'up', '-d'], check=True)


def stop():
    print("Stop")
    subprocess.run(['docker-compose', '-f', f'{SCRIPT_DIR}/docker-compose.yml', 'down'], check=True)


dispatcher = {'start': start, 'stop': stop}


def main():
    parser = argparse.ArgumentParser(description='Manage the infrastructure', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("action_command", help="set action command", default='start', choices=['start', 'stop'],
                        nargs='?')
    args = parser.parse_args()
    dispatcher[args.action_command]()


if __name__ == '__main__':
    main()

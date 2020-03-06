#!/usr/bin/env python3

import docker
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='This is the docker image builder for quarkus-todo-app')
    parser.add_argument("build_type", help="set build type", default='jvm', choices=['jvm', 'native'], nargs='?')
    args = parser.parse_args()

    print(f'build_type={args.build_type}')

    dockerfile = Path.cwd() / 'src' / 'main' / 'docker' / f'Dockerfile.{args.build_type}'

    print(f'docker_file={dockerfile}')

    client = docker.from_env()
    client.images.build(path="./",
                        dockerfile=dockerfile.resolve(),
                        tag=f'quarkus-todo-app-{args.build_type}')


if __name__ == '__main__':
    main()

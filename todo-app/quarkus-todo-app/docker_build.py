#!/usr/bin/env python3

import argparse
import re
import subprocess
from pathlib import Path

import docker


def main():
    parser = argparse.ArgumentParser(description='This is the docker image builder for quarkus-todo-app')
    parser.add_argument("build_type", help="set build type", default='jvm', choices=['jvm', 'native'], nargs='?')
    args = parser.parse_args()

    print(f'build_type={args.build_type}')

    build_type = args.build_type
    if args.build_type == 'jvm':
        java_version = re.search(r'\"(\d+\.\d+).*\"',
                                 str(subprocess.check_output(['java', '-version'],
                                                             stderr=subprocess.STDOUT))).group(1)
        if java_version.startswith('11'):
            build_type = f'{build_type}11'

    source_dir = Path(__file__).parent.resolve()
    dockerfile = source_dir / 'src' / 'main' / 'docker' / f'Dockerfile.{build_type}'

    print(f'docker_file={dockerfile}')

    client = docker.from_env()
    client.images.build(path=f'{source_dir}',
                        dockerfile=dockerfile.resolve(),
                        tag=f'quarkus-todo-app-{args.build_type}')


if __name__ == '__main__':
    main()

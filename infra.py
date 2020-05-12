#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path

import docker
from docker.errors import NotFound
from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.client.rest import ApiException

from tools.app_utils import read_dot_env_file
from tools.globals import *

INFRA_DIR = Path(__file__).cwd() / 'infra'


class InfraManager:

    def __init__(self):
        self.dockerClient = docker.from_env()

    def setup(self):
        self.create_log_folder()
        self.create_env_file()
        self.build_infra_db_image()

    @staticmethod
    def create_log_folder():
        print(f'creating {DEFAULT_LOG_FOLDER} folder')
        Path(DEFAULT_LOG_FOLDER).mkdir(exist_ok=True)

    @staticmethod
    def create_env_file():
        print(f'checking {ENV_FILE} file... ', end='')
        if not Path(ENV_FILE).is_file():
            print('failed!')
            db_user = input("Enter db USERNAME [admin]: ") or "admin"
            db_pass = input("Enter db PASSWORD [admin]: ") or "admin"
            f = open(ENV_FILE, "w+")
            f.writelines([f'POSTGRES_USER={db_user}\n',
                          f'POSTGRES_PASSWORD={db_pass}\n',
                          f'POSTGRES_MULTIPLE_DATABASES={",".join(DATABASES)}\n',
                          f'POSTGRES_DB_HOST={DATABASE_HOST}\n'])
        else:
            print('ok!')

    def build_infra_db_image(self):
        self.dockerClient.images.build(path=f'{INFRA_DIR}/infra-db', tag='infra-db:1.0.0')

    def start(self):
        pass

    def stop(self):
        pass


class DCInfraManager(InfraManager):

    def setup(self):
        super(DCInfraManager, self).setup()
        self.create_network()

    def create_network(self):
        try:
            print('checking network settings... ', end='')
            self.dockerClient.networks.get(DOCKER_TODO_APP_NETWORK)
            print('ok!')
        except NotFound:
            print('failed!')
            print("creating network for todo-apps", end='')
            self.dockerClient.networks.create(DOCKER_TODO_APP_NETWORK)
            print('done!')

    def start(self):
        self.setup()
        subprocess.run(['docker-compose', '-f', f'{INFRA_DIR}/docker-compose.yml', 'up', '-d'], check=True)

    def stop(self):
        subprocess.run(['docker-compose', '-f', f'{INFRA_DIR}/docker-compose.yml', 'down'], check=True)


class K8SInfraManager(InfraManager):
    INFRA_DB_DEPLOYMENT = 'infra-db-deployment'
    INFRA_DB_SERVICE = 'infra-db'
    INFRA_YAML = 'k8s-infra.yaml'
    PROMETHEUS_SERVER_DEPLOYMENT = 'prometheus-deployment'
    PROMETHEUS_SERVER_SERVICE = 'infra-prometheus'
    PROMETHEUS_SERVER_CONFIG = 'prometheus-server-conf'
    GRAFANA_DEPLOYMENT = 'grafana-deployment'
    GRAFANA_SERVICE = 'infra-grafana'
    GRAFANA_DATASOURCES_CONFIG = 'grafana-datasources'
    GRAFANA_DASHBOARDS_CONFIG = 'grafana-dashboards'

    def __init__(self):
        super(K8SInfraManager, self).__init__()
        k8s_config.load_kube_config()
        self.coreApi = k8s_client.CoreV1Api()
        self.appsApi = k8s_client.AppsV1Api()

    def setup(self):
        super(K8SInfraManager, self).setup()
        self.__create_namespace()
        self.__create_infra_db_config_map()
        self.__create_prometheus_config_map()
        self.__create_grafana_config_maps()

    def __create_namespace(self):
        print(f'checking {TODO_APP_NAMESPACE} namespace settings... ', end='')
        res = self.coreApi.list_namespace(field_selector=f'metadata.name={TODO_APP_NAMESPACE}')
        if not len(res.items):
            print('failed!')
            print("creating namespace for todo-apps", end='')
            ns = k8s_client.V1Namespace(metadata=k8s_client.V1ObjectMeta(name=TODO_APP_NAMESPACE))
            self.coreApi.create_namespace(body=ns)
            print("done!")
        else:
            print('ok!')

    def __create_infra_db_config_map(self):
        config_data = read_dot_env_file(ENV_FILE)
        self.__create_config_map(name=INFRA_DB_CONFIG, config_data=config_data)

    def __create_prometheus_config_map(self):
        self.__create_config_map(name=self.PROMETHEUS_SERVER_CONFIG,
                                 config_files=[f'{INFRA_DIR}/prometheus/prometheus.yml'])

    def __create_grafana_config_maps(self):
        self.__create_config_map(name=self.GRAFANA_DATASOURCES_CONFIG,
                                 config_files=[f'{INFRA_DIR}/grafana/datasources/datasource.yml'])
        self.__create_config_map(name=self.GRAFANA_DASHBOARDS_CONFIG,
                                 config_files=[f'{INFRA_DIR}/grafana/dashboards/dashboard.yml',
                                               f'{INFRA_DIR}/grafana/dashboards/JVM-Micrometer-1583529689446.json',
                                               f'{INFRA_DIR}/grafana/dashboards/Micrometer-Spring-Throughput-1583529634093.json'])

    def __create_config_map(self, name, config_data=None, config_files=None):
        print(f'checking {name} configmap settings... ', end='')
        res = self.coreApi.list_namespaced_config_map(namespace=TODO_APP_NAMESPACE,
                                                      field_selector=f'metadata.name={name}')
        if not len(res.items):
            print('failed!')
            print(f'creating {name} configmap ', end='')
            config_map = k8s_client.V1ConfigMap(metadata=k8s_client.V1ObjectMeta(name=name), data=config_data)
            if config_data:
                self.coreApi.create_namespaced_config_map(namespace=TODO_APP_NAMESPACE, body=config_map)
            elif config_files:
                command = ['kubectl', 'create', 'configmap', name, '--namespace', TODO_APP_NAMESPACE]
                for config_file in config_files:
                    command.append('--from-file')
                    command.append(config_file)

                subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
            print("done!")
        else:
            print('ok!')

    def start(self):
        self.setup()
        res = self.appsApi.list_namespaced_deployment(namespace=TODO_APP_NAMESPACE,
                                                      field_selector=f'metadata.name={self.INFRA_DB_DEPLOYMENT}')
        if len(res.items):
            print(f'{self.INFRA_DB_DEPLOYMENT} deployment is running')
        else:
            from kubernetes.utils import create_from_yaml
            create_from_yaml(k8s_client=k8s_client.ApiClient(), yaml_file=f'{INFRA_DIR}/{self.INFRA_YAML}',
                             namespace=TODO_APP_NAMESPACE)

    def stop(self):
        self.stop_infra_db()
        self.stop_prometheus()
        self.stop_grafana()

    def stop_infra_db(self):
        self.__delete_deployment(name=self.INFRA_DB_DEPLOYMENT)
        self.__delete_service(name=self.INFRA_DB_SERVICE)
        self.__delete_config_map(name=INFRA_DB_CONFIG)

    def stop_prometheus(self):
        self.__delete_deployment(name=self.PROMETHEUS_SERVER_DEPLOYMENT)
        self.__delete_service(name=self.PROMETHEUS_SERVER_SERVICE)
        self.__delete_config_map(name=self.PROMETHEUS_SERVER_CONFIG)

    def stop_grafana(self):
        self.__delete_deployment(name=self.GRAFANA_DEPLOYMENT)
        self.__delete_service(name=self.GRAFANA_SERVICE)
        self.__delete_config_map(name=self.GRAFANA_DATASOURCES_CONFIG)
        self.__delete_config_map(name=self.GRAFANA_DASHBOARDS_CONFIG)

    def __delete_deployment(self, name):
        try:
            print(f'deleting {name} deployment.. ', end='')
            self.appsApi.delete_namespaced_deployment(namespace=TODO_APP_NAMESPACE, name=name)
            print('done!')
        except ApiException:
            print('failed!')

    def __delete_service(self, name):
        try:
            print(f'deleting {name} service.. ', end='')
            self.coreApi.delete_namespaced_service(namespace=TODO_APP_NAMESPACE, name=name)
            print('done!')
        except ApiException:
            print('failed!')

    def __delete_config_map(self, name):
        try:
            print(f'deleting {name} config-map.. ', end='')
            self.coreApi.delete_namespaced_config_map(namespace=TODO_APP_NAMESPACE, name=name)
            print('done!')
        except ApiException:
            print('failed!')


def main():
    parser = argparse.ArgumentParser(description='Manage the infrastructure',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-p", "--platform", help="set platform type", default='docker', choices=['docker', 'k8s'])
    parser.add_argument("action_command", help="set action command", default='start', choices=['start', 'stop'],
                        nargs='?')
    args = parser.parse_args()

    managers = {'docker': DCInfraManager, 'k8s': K8SInfraManager}
    getattr(managers[args.platform](), args.action_command)()


if __name__ == '__main__':
    main()

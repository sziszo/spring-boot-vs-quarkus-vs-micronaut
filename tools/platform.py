import json
import logging.config
import re
import time

import docker
from docker.errors import NotFound
from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.client import V1LabelSelector, V1ObjectMeta, V1DeploymentSpec, V1PodTemplateSpec, V1PodSpec, \
    V1Container, V1ContainerPort, V1EnvFromSource, V1ConfigMapEnvSource, V1Deployment
from kubernetes.client.rest import ApiException

from .app_utils import bytesto
from .globals import *

LOGGER = logging.getLogger(__name__)


def set_verbose():
    LOGGER.setLevel('DEBUG')


class PlatformException(Exception):
    pass


class PlatformManager:
    MAX_ATTEMPT = 10

    def start_app(self):
        pass

    def stop_app(self):
        pass

    def memory_usage(self):
        pass

    def logs(self):
        pass


class DockerPlatformManager(PlatformManager):

    def __init__(self, image_name, container_name, container_port, host_port=None):
        self.image_name = image_name
        self.container_name = container_name
        self.container_port = container_port
        self.host_port = host_port if host_port else container_port
        self.client = docker.from_env()
        self.container = None

    def stop_app(self):
        try:
            container = self.client.containers.get(self.container_name)
            LOGGER.warning(f'{self.container_name} container is running')
            container.stop()
            LOGGER.info(f'{self.container_name} container is stopped')
            time.sleep(0.5)
        except NotFound:
            LOGGER.info(f'{self.container_name} is not running')

    def start_app(self):
        LOGGER.info(f'Starting {self.image_name} container ...')
        self.container = self.client.containers.run(self.image_name,
                                                    name=f'{self.container_name}',
                                                    detach=True,
                                                    remove=True,
                                                    network='todo_app_network',
                                                    ports={f'{self.container_port}/tcp': self.host_port},
                                                    environment=["POSTGRES_DB_HOST=infra-db"])

    def memory_usage(self):
        # container = self.client.containers.get(self.container_name)
        if not self.container:
            return 0
        stats = self.container.stats(stream=False)
        return round(bytesto(stats["memory_stats"]["usage"]), 1)

    def logs(self):
        if not self.container:
            return None
        return self.container.logs(stream=True)


class KubernetesPlatformManager(PlatformManager):
    MEMORY_USAGE_PATTERN = re.compile(r'([0-9]+)([a-zA-Z]+)')

    def __init__(self, image_name, container_name, container_port, host_port=None):
        self.image_name = image_name
        self.container_name = container_name
        self.container_port = container_port
        self.host_port = host_port if host_port else container_port
        k8s_config.load_kube_config()
        self.appsApi = k8s_client.AppsV1Api()
        self.coreApi = k8s_client.CoreV1Api()
        self.apiClient = k8s_client.ApiClient()

    def start_app(self):
        labels = {'app': self.container_name}
        container_port = V1ContainerPort(container_port=self.container_port)
        config_map_ref = V1ConfigMapEnvSource(name=INFRA_DB_CONFIG)
        container = V1Container(name=self.container_name, image=self.image_name, image_pull_policy='IfNotPresent',
                                ports=[container_port], env_from=[V1EnvFromSource(config_map_ref=config_map_ref)])
        pod_spec = V1PodSpec(containers=[container])
        pod_temp_spec = V1PodTemplateSpec(metadata=V1ObjectMeta(name=self.container_name, labels=labels), spec=pod_spec)
        deployment_spec = V1DeploymentSpec(replicas=1, selector=V1LabelSelector(match_labels=labels),
                                           template=pod_temp_spec)
        deployment = V1Deployment(metadata=V1ObjectMeta(name=self.container_name), spec=deployment_spec)

        self.appsApi.create_namespaced_deployment(namespace=TODO_APP_NAMESPACE, body=deployment)

    def stop_app(self):
        res = self.appsApi.list_namespaced_deployment(namespace=TODO_APP_NAMESPACE,
                                                      field_selector=f'metadata.name={self.container_name}')
        if not len(res.items):
            LOGGER.info(f'{self.container_name} deployment is not running')
        else:
            LOGGER.warning(f'{self.container_name} deployment is running')
            self.appsApi.delete_namespaced_deployment(name=self.container_name, namespace=TODO_APP_NAMESPACE)
            time.sleep(5)
            LOGGER.info(f'{self.container_name} deployment is stopped')

    def memory_usage(self):
        pod_name = self.__get_running_pod()
        mem_usage = '0Ki'
        done = False
        attempt = 0
        while not done and attempt < self.MAX_ATTEMPT:
            try:
                ret_metrics = self.apiClient.call_api(
                    f'/apis/metrics.k8s.io/v1beta1/namespaces/{TODO_APP_NAMESPACE}/pods/{pod_name}', 'GET',
                    auth_settings=['BearerToken'], response_type='json', _preload_content=False)
                response = json.loads(ret_metrics[0].data.decode('utf-8'))
                mem_usage = response['containers'][0]['usage']['memory']
                LOGGER.debug(f'mem_usage={mem_usage}')
            except (ApiException, IOError):
                sleeping_time = 10
                LOGGER.info(f'attempt {attempt+1}: sleeping {sleeping_time} sec to get the metrics of {pod_name}')
                time.sleep(sleeping_time)
                attempt += 1
            else:
                done = True

        if attempt == self.MAX_ATTEMPT:
            LOGGER.error(f'reached the maximum attempt to get the metrics of {pod_name}')

        match = re.search(self.MEMORY_USAGE_PATTERN, mem_usage)
        return round(bytesto(int(match.group(1)), from_=match.group(2)), 1)

    def logs(self):
        pod_name = self.__get_running_pod()
        return self.coreApi.read_namespaced_pod_log(namespace=TODO_APP_NAMESPACE, name=pod_name, pretty=True,
                                                    follow=True, _preload_content=False).stream()

    def __get_running_pod(self):
        running_pod = None
        attempt = 0
        while not running_pod and attempt < self.MAX_ATTEMPT:
            pods = self.coreApi.list_namespaced_pod(namespace=TODO_APP_NAMESPACE,
                                                    label_selector=f'app={self.container_name}')
            for pod in pods.items:
                pod_name = pod.metadata.name
                try:
                    if pod.status.container_statuses[0].state.running:
                        LOGGER.debug(f'attempt {attempt+1}: {pod_name} pod is running')
                        running_pod = pod
                        break
                except TypeError:
                    pass

                if not running_pod:
                    try:
                        if pod.status.container_statuses[0].state.terminated:
                            LOGGER.debug(f'attempt {attempt+1}: {pod_name} pod is terminating')
                    except TypeError:
                        pass

            if not running_pod:
                sleeping_time = 1
                LOGGER.debug(f'attempt {attempt+1}: sleeping {sleeping_time} sec to get the running pod for {self.container_name}')
                time.sleep(sleeping_time)
                attempt += 1

        if attempt == self.MAX_ATTEMPT:
            raise PlatformException(f'reached the maximum attempt to get the running pod for {self.container_name}')

        return running_pod.metadata.name if running_pod else None


class PlatformManagerFactory:
    platformManagers = {'docker': DockerPlatformManager, 'k8s': KubernetesPlatformManager}

    @staticmethod
    def create(platform, image_name, container_name, container_port, host_port=None):
        return PlatformManagerFactory.platformManagers[platform](image_name, container_name, container_port, host_port)

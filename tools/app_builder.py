import logging
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from .app_utils import get_image_name
from .globals import DEFAULT_LOG_FOLDER

LOGGER = logging.getLogger(__name__)


def set_verbose():
    LOGGER.setLevel('DEBUG')


class AppBuilder:
    def __init__(self):
        self.buildAppTime = 0

    def build(self):
        pass

    def build_app(self, path, output_file='build.out'):
        LOGGER.info(f'building {path} app')
        start_time = time.time()
        build_output = open(output_file, 'w+')
        subprocess.run(["./mvnw", "clean", "package", "-DskipTests", "-pl", path],
                       check=True,
                       stdout=build_output,
                       stderr=build_output)
        end_time = time.time()
        self.buildAppTime = round(end_time - start_time, 3)
        LOGGER.debug(f'building {path} app took {self.buildAppTime}s')

    def build_image(self, path, image_name, output_file):
        pass

    @staticmethod
    def to_result_table(app_name, build_app_time, build_image_time):
        table = defaultdict(dict)
        table[app_name]["app-build-time"] = f'{build_app_time}s'
        table[app_name]["image-build-time"] = f'{build_image_time}s'
        return table


class SpringAppBuilder(AppBuilder):
    def __init__(self, path):
        super(SpringAppBuilder, self).__init__()
        self.path = path
        self.app_name = Path(path).stem
        self.output_file = f'{DEFAULT_LOG_FOLDER}/{self.app_name}.out'
        self.buildImageTime = 0

    def build(self):
        image_name = f'{self.app_name}'
        self.build_app(self.path, self.output_file)
        time.sleep(0.5)
        self.build_image(self.path, image_name, self.output_file)
        return self.to_result_table(image_name, self.buildAppTime, self.buildImageTime)

    def build_image(self, path, image_name, output_file):
        LOGGER.info(f'creating {image_name} docker image')
        start_time = time.time()
        build_output = open(output_file, 'a+')
        subprocess.run(["./mvnw", "jib:dockerBuild", "-pl", path],
                       check=True,
                       stdout=build_output,
                       stderr=build_output)
        end_time = time.time()
        self.buildImageTime = round(end_time - start_time, 3)
        LOGGER.debug(f'creating {image_name} docker image took {self.buildImageTime}s')


class QuarkusAppBuilder(AppBuilder):
    def __init__(self, path, build_type='jvm'):
        super(QuarkusAppBuilder, self).__init__()
        self.path = path
        self.build_type = build_type
        self.app_name = Path(path).stem
        self.output_file = f'{DEFAULT_LOG_FOLDER}/{self.app_name}-{self.build_type}.out'
        self.image_name = get_image_name(path, build_type)
        self.buildImageTime = 0

    def build(self):
        self.build_app(self.path, self.output_file)
        time.sleep(0.5)
        self.build_image(self.path, self.image_name, self.output_file)
        return self.to_result_table(self.image_name, self.buildAppTime, self.buildImageTime)

    def build_app(self, path, output_file='build.out'):
        if self.build_type == 'jvm':
            super().build_app(path, output_file)
        else:
            self.__build_native_quarkus_app(path, output_file)

    def __build_native_quarkus_app(self, path, output_file='build.out'):
        LOGGER.info(f'building {path} app')
        start_time = time.time()
        build_output = open(output_file, 'w+')
        subprocess.run(["./mvnw", "clean", "package", "-DskipTests",
                        "-Pnative", "-Dquarkus.native.container-build=true",
                        "-Dquarkus.native.container-runtime=docker",
                        "-pl", path],
                       check=True,
                       stdout=build_output,
                       stderr=build_output)
        end_time = time.time()
        self.buildAppTime = round(end_time - start_time, 3)
        LOGGER.debug(f'building {path} app took {self.buildAppTime}s')

    def build_image(self, path, image_name, output_file):
        LOGGER.info(f'creating {image_name} docker image')
        start_time = time.time()
        build_output = open(output_file, 'a+')
        image_builder = Path(path) / 'docker_build.py'
        subprocess.run([image_builder.resolve(), self.build_type],
                       check=True,
                       stdout=build_output,
                       stderr=build_output)
        end_time = time.time()
        self.buildImageTime = round(end_time - start_time, 3)
        LOGGER.debug(f'creating {image_name} docker image took {self.buildImageTime}s')

# spring-boot-vs-quarkus-vs-micronaut
The goal is to compare Quarkus, Micronaut and Spring Boot by measuring start-up times and memory footprint.

## Prerequisite 
 
* Python3
* [Docker SDK for Python](https://docker-py.readthedocs.io/en/stable/)
* [Pandas](https://pypi.org/project/pandas/)
* [PyYaml](https://pypi.org/project/PyYAML/)

```shell script
$ pip install docker
$ pip install pandas
$ pip install pyaml
```

## Run  
To compare all kind of Todo apps in docker just execute
```shell script
./build_and_run.py
```

You can specify the app-type and/or build-type to build and run only a set of application 
* app-type: type of the application (spring or quarkus)
* build-type: type of the build (jvm or native)

```shell script
./build_and_run.py -t {app-type} {build-type}
```




#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: infra.sh start|stop"
    exit 1
fi

for i in "$@"
do
case $i in
 start)
   START=true
   ;;
 stop)
   STOP=true
   ;;
 *)
   ;;
esac
done

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

function start() {
  if [[ ! -f .env ]]; then
    read -p 'Enter db USERNAME [admin]: ' USERNAME
    USERNAME=${USERNAME:-admin}
    read -sp 'Enter db PASSWORD [admin]: ' PASSWORD
    PASSWORD=${PASSWORD:-admin}
    echo -e
    echo -e "DB_USER=${USERNAME}\nDB_PASSWORD=${PASSWORD}\n" >> .env
  fi

  docker-compose -f "${SCRIPT_DIR}/docker-compose.yml" up -d
}

function stop() {
  docker-compose -f "${SCRIPT_DIR}/docker-compose.yml" down
}

if [ "$START" = true ]
then
  start
elif [ "$STOP" = true ]
then
  stop
fi


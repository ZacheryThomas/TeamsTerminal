__author__ = 'Zachery Thomas'

import time
import docker

CLIENT = docker.from_env()

while True:
    for container in CLIENT.containers.list():
        res = container.exec_run('ls')

        if res.exit_code == 126:
            print('killing: {}'.format(container.name))
            container.stop()
            container.remove()

    time.sleep(10)
__author__ = 'Zachery Thomas'

import os
import json
import time
import threading
import random

import docker
import requests
import bottle
from bottle import post, request, run

CLIENT = docker.from_env()

BEARER = os.getenv('BEARER')
MYID = os.getenv('MYID')
HEADERS = {"Authorization": "Bearer {}".format(BEARER)}


def start_container(name):
    """Starts container with a given container name"""
    container = CLIENT.containers.run('teamsterminal_docker', ['tail', '-f', '/dev/null'],
                                      cpu_percent=10,
                                      mem_limit='25m',
                                      name=str(name),
                                      detach=True)
    return container


def run_command(container, cmd):
    """Runs command given container obj and cmd string"""
    cmd = 'sh -c "{}"'.format(str(cmd))

    try:
        res = container.exec_run(cmd)
        print('exit_code: {}, output: {}'.format(res.exit_code, res.output.decode('utf-8')))
        return res.output.decode('utf-8'), res.exit_code
    except Exception as exc:
        return str(exc), 1


class WortherThread (threading.Thread):
    def __init__(self, container):
        threading.Thread.__init__(self)
        self.container = container
        self.timeout = 10
        self._running = True
        self.completed = True

    def run(self):
        while self._running and self.timeout > 0:
            print('Timeout in: ', self.timeout, ' seconds')
            self.timeout -= 1
            time.sleep(1)

        if self.timeout == 0:
            self.container.stop()
            self.container.remove()

    def terminate(self):
        self._running = False



@post('/messages')
def messages():
    print('got post!')
    data = json.loads(request.body.read())['data']

    roomId = data['roomId']
    personId = data['personId']
    messageId = data['id']

    # Ban Adam Davis
    if personId == '<ADAM DAVIS\' PERSONAL ID>':
        adam_resposnes = [
            'Oh no, im not falling for that again Adam.',
            'Nice try, bucko!',
            'Beep boop!'
        ]

        res = requests.post(url = "https://api.ciscospark.com/v1/messages",
                    headers = HEADERS,
                    data = {
                                "markdown": '{} Adam is banned!'.format(random.choice(adam_resposnes)),
                                "roomId": roomId
                            })

        return

    print(personId, MYID)
    if personId == MYID:
        return

    res = requests.get(url = "https://api.ciscospark.com/v1/messages/{}".format(messageId),
                headers = HEADERS)

    print(res.json())
    text = res.json()['text']
    text = text.replace('Terminal', '')
    text = text.strip()

    print('text: {}'.format(text))
    print('container name: {}'.format(roomId))
    try:
        container = CLIENT.containers.get(roomId)

    except docker.errors.NotFound:
        print('Container not found for {}, starting one...'.format(roomId))
        container = start_container(roomId)
        print('Started container for {}'.format(roomId))

    wt = WortherThread(container)
    wt.start()


    res_text, res_code = run_command(container, text)
    wt.terminate()
    print(res_text, res_code)


    # post resposne to room as joeybot
    res = requests.post(url = "https://api.ciscospark.com/v1/messages",
                headers = HEADERS,
                data = {
                            "markdown": """```bash
>_ {}

{}
```""".format(text, res_text),
                            "roomId": roomId
                        })

    print(res.text)
    print('response from bot post: {}'.format(res.json()))


if __name__ == "__main__":
    run(host='0.0.0.0', port=80)
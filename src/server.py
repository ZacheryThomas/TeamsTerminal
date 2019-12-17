__author__ = 'Zachery Thomas'

import re
import os
import json
import time
import threading
import random

import docker
import requests
from bottle import post, request, run

CLIENT = docker.from_env()

BEARER = os.getenv('BEARER')
MYID = os.getenv('MYID')
HEADERS = {"Authorization": "Bearer {}".format(BEARER)}

MAX_MSG_LEN = 7000
TIMEOUT = 10


def format_text(text):
    """Formats text to right input for sh command"""

    chars = {
        '“': '"',
        '”': '"',
        '‘': "'",
        '’': "'",
        '“': '"',
        '”': '"',
        '"': '"',
    }

    text = text.replace('Terminal', '')

    for char in chars:
        text = text.replace(char, chars[char])

    text = text.strip()
    return text


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
    cmd = 'sh -c """{}"""'.format(str(cmd))
    print('cmd: ', cmd)

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
        self.timeout = TIMEOUT
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
    text = format_text(text)

    res = requests.get(url = "https://api.ciscospark.com/v1/rooms/{}".format(roomId),
                headers = HEADERS)

    room_name =res.json()['title']
    container_name = roomId[-10:] + '_' + re.sub('[\W]', '_', room_name)

    print('text: {}'.format(text))
    print('container name: {}'.format(container_name))
    try:
        container = CLIENT.containers.get(container_name)

    except docker.errors.NotFound:
        print('Container not found for {}, starting one...'.format(container_name))
        container = start_container(container_name)
        print('Started container for {}'.format(container_name))

    wt = WortherThread(container)
    wt.start()


    res_text, res_code = run_command(container, text)
    wt.terminate()
    print(res_text, res_code)

    if len(res_text) >= MAX_MSG_LEN:
        res_text = res_text[0:int(MAX_MSG_LEN / 4)] + '\n...\n' + res_text[- int(MAX_MSG_LEN / 4):]


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
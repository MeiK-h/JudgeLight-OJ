# coding=utf-8
from config import Config

import json
import redis

rdp = redis.ConnectionPool(host=Config.redisHost, port=Config.redisPort)
rdc = redis.StrictRedis(connection_pool=rdp)


def add_judger_to_list(judger):
    rdc.rpush(Config.redisList, judger.run_id)


def get_judge_list():
    _l = rdc.llen(Config.redisList)
    judge_list = rdc.lrange(Config.redisList, 0, _l)
    judge_list_data = []
    for i in judge_list:
        judge_list_data.append(bytes.decode(i))
    return judge_list_data


def get_task():
    task = rdc.blpop(Config.redisList)
    run_id = bytes.decode(task[1])
    return run_id


class Judger(object):
    keys = ['run_id', 'pid', 'language', 'code', 'time_limit', 'memory_limit']

    def __init__(self, run_id):
        self.run_id = str(run_id)
        self.pid = None
        self.language = None
        self.code = None
        self.time_limit = None
        self.memory_limit = None
        self.result = None
        self.other = None
        data = rdc.hget(Config.redisResult, run_id)
        if data:
            self.data = json.loads(data)

    @property
    def data(self):
        _data = {
            'run_id': self.run_id,
            'pid': self.pid,
            'language': self.language,
            'code': self.code,
            'time_limit': self.time_limit,
            'memory_limit': self.memory_limit,
        }
        if self.result:
            _data['result'] = self.result
        if self.other:
            _data.update(self.other)
        return _data

    @data.setter
    def data(self, data):
        """
        Parse the data in data into a class object
        """
        # Judge that data contains all the required parameters
        assert all(map(self.data.__contains__, self.keys))
        self.pid = data.pop('pid')
        self.language = data.pop('language')
        self.code = data.pop('code')
        self.time_limit = int(data.pop('time_limit'))
        self.memory_limit = int(data.pop('memory_limit'))
        if 'result' in data.keys():
            self.result = data.pop('result')
        self.other = data

    def update(self):
        assert all(map(self.data.__contains__, self.keys))
        rdc.hset(Config.redisResult, self.run_id, json.dumps(self.data))

    def delete(self):
        if rdc.hget(Config.redisResult, self.run_id):
            rdc.hdel(Config.redisResult, self.run_id)


class Result(object):
    def __init__(self):
        """
        {
            compiler: Runner
            result: [
                {
                    runner: Runner,
                    checker: Runner
                },
                ...
            ]
        }
        """
        self.compiler = None
        self.result = None


class Runner(object):
    def __init__(self):
        """
        {
            state: int
            message: str
            time_used: int
            memory_used: int
        }
        """
        self.state = None
        self.message = None
        self.time_used = None
        self.memory_used = None

    def parse_data(self, data):
        self.state = data['state']
        self.message = data['message']
        self.time_used = data['time_used']
        self.memory_used = data['memory_used']

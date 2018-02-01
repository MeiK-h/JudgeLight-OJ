# coding=utf-8
import os
import json
import shutil
import docker
import requests
from config import Config, Judge


def update(run_id, msg, result=None, json_data=False):
    if json_data is False:
        data = {
            'msg': msg,
            'result': result
        }
        requests.post('http://127.0.0.1:8000/{}/'.format(run_id), data=data)
    else:
        data = {
            'msg': 'result update',
            'name': 'judge',
            'judge': json.dumps(msg),
            'json': True
        }
        requests.post('http://127.0.0.1:8000/{}/'.format(run_id), data=data)


def init(data):
    """ 进入 docker 之前的初始化操作 """
    run_id = data['args']['run_id']
    pid = data['args']['pid']
    language = data['args']['language']
    code = data['args']['code']
    time_limit = int(data['args']['time_limit'])
    memory_limit = int(data['args']['memory_limit'])

    update(run_id, 'init start')
    work_dir = os.path.join(Config.workDir, run_id)
    work_data_dir = os.path.join(work_dir, 'data')
    os.mkdir(work_data_dir)  # 创建数据目录
    data_json_file = os.path.join(Config.dataDir, pid, 'judge.json')
    with open(data_json_file) as data_json:
        data_json = json.loads(data_json.read())
        for data_file in data_json['data']:  # 复制数据文件
            shutil.copy(os.path.join(Config.dataDir, pid, data_file["in"]), work_data_dir)

        data_json.update({
            'file': Judge.cmd[language]['file'],
            'compile_cmd': Judge.cmd[language]['compile'],
            'run_cmd': Judge.cmd[language]['run'],
            'compile_time_limit': Judge.compile_time_limit,
            'compile_memory_limit': Judge.compile_memory_limit,
            'time_limit': time_limit,
            'memory_limit': memory_limit
        })
        data_json['args'] = data['args']
        with open(os.path.join(work_dir, 'judge.json'), 'w') as judge_json:  # 写入评测配置
            judge_json.write(json.dumps(data_json))
        with open(os.path.join(work_dir, Judge.cmd[language]['file']), 'w') as code_file:  # 写入代码
            code_file.write(code)

    shutil.copy(os.path.join(Config.dataDir, pid, 'judge.py'), os.path.join(Config.workDir, run_id))  # 复制 judge.py
    shutil.copy(os.path.join(Config.dataDir, pid, 'check.py'), os.path.join(Config.workDir, run_id))  # 复制 check.py
    update(run_id, 'init end')


def run_in_docker(data):
    run_id = data['args']['run_id']
    update(run_id, 'running in docker')
    devices = os.path.join(os.path.abspath(Config.workDir), run_id)
    volumes = {
        devices: {
            'bind': '/work',
            'mode': 'rw'
        }
    }
    client = docker.from_env()
    client.containers.run(
        image=Config.dockerImage,  # docker 的镜像名
        command="python3 judge.py",  # 进入之后执行的操作
        auto_remove=True,  # 运行结束之后自动清理
        cpuset_cpus='1',  # 可使用的 CPU 核数
        network_disabled=True,  # 禁用网络
        network_mode='none',  # 禁用网络
        volumes=volumes,  # 加载数据卷
        working_dir='/work'  # 进入之后的工作目录
    )
    update(run_id, 'docker running end')


def check(data):
    """ 结果评测 """
    run_id = data['args']['run_id']
    update(run_id, 'check start')
    pid = data['args']['pid']
    data_json_file = os.path.join(Config.dataDir, pid, 'judge.json')
    work_dir = os.path.join(Config.workDir, run_id)
    work_data_dir = os.path.join(work_dir, 'data')
    with open(data_json_file) as data_json:
        data_json = json.loads(data_json.read())
        for data_file in data_json['data']:  # 复制数据文件
            shutil.copy(os.path.join(Config.dataDir, pid, data_file["out"]), work_data_dir)
    os.system('python3 {} {}'.format(os.path.join(work_dir, 'check.py'), work_dir))
    update(run_id, 'check end')
    with open(os.path.join(work_dir, 'judge_out.json')) as f:
        return json.loads(f.read())


def main(data):
    data = json.loads(data)
    run_id = data['args']['run_id']
    try:
        init(data)
        run_in_docker(data)
        rst = check(data)
        update(run_id, rst, json_data=True)
        update(run_id, 'judge end', result=rst['result'])
    except Exception as e:
        update(run_id, e)
    else:
        pass

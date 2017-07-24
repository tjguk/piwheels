from .cmdline import Cmd
from .db import PiWheelsDatabase
from .. import __version__

class PiWheelsCmd(Cmd):
    prompt = 'PW: '

    def __init__(self):
        Cmd.__init__(self)
        self.pprint('PiWheels Master version {}'.format(__version__))
        self.pprint(
            'Type "help" for more information, '
            'or "find" to locate PiWheels slaves')

    def preloop(self):
        self.terminate = Event()
        self.db = PiWheelsDatabase()
        self.ctx = zmq.Context()
        self.build_queue = ctx.socket(zmq.PUSH)
        self.build_queue.ipv6 = True
        self.build_queue.bind('tcp://*:5555')
        self.log_queue = ctx.socket(zmq.PULL)
        self.log_queue.ipv6 = True
        self.log_queue.bind('tcp://*:5556')
        self.ctrl_queue = ctx.socket(zmq.PUB)
        self.ctrl_queue.ipv6 = True
        self.ctrl_queue.bind('tcp://*:5557')
        self.pkg_thread = Thread(target=self.update_pkgs, daemon=True)
        self.job_thread = Thread(target=self.queue_jobs, daemon=True)
        self.log_thread = Thread(target=self.log_results, daemon=True)
        self.pkg_thread.start()
        self.job_thread.start()
        self.log_thread.start()

    def postloop(self):
        self.terminate.set()
        self.job_thread.join()
        self.log_thread.join()
        self.pkg_thread.join()
        self.ctrl_queue.send_json('QUIT')
        self.build_queue.close()
        self.log_queue.close()
        self.ctrl_queue.close()
        self.ctx.term()

    def update_pkgs(self):
        with PiWheelsDatabase() as db:
            while not terminate.wait(60):
                db.update_package_list()
                db.update_package_version_list()

    def queue_jobs(q):
        with PiWheelsDatabase() as db:
            while not stop.wait(5):
                if idle.wait(0):
                    for package, version in db.get_build_queue():
                        q.send_json((package, version))
                        if stop.wait(0): # check stop regularly
                            break
                    idle.clear()

    def log_results(q):
        with PiWheelsDatabase() as db:
            while not stop.wait(0):
                events = q.poll(10000)
                if events:
                    msg = q.recv_json()
                    if msg == 'IDLE':
                        print('!!! Idle builder found')
                        idle.set()
                    else:
                        db.log_build(*msg)


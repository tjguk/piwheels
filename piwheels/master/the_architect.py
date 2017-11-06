import zmq
from collections import deque, defaultdict
from datetime import datetime, timedelta

from .tasks import Task
from .db import Database


class TheArchitect(Task):
    """
    This task queries the backend database to determine which versions of
    packages have yet to be built (and aren't marked to be skipped). It places a
    tuple of (package, version) for each such build into the internal "builds"
    queue for :class:`SlaveDriver` to read.
    """
    name = 'master.the_architect'

    def __init__(self, config):
        super().__init__(config)
        self.db = Database(config['database'])
        build_queue = self.ctx.socket(zmq.REP)
        build_queue.hwm = 1
        build_queue.bind(config['build_queue'])
        self.query = None
        self.timestamp = datetime.utcnow() - timedelta(seconds=30)
        self.abi_queues = defaultdict(lambda: deque(maxlen=1000))
        self.register(build_queue, self.handle_build)

    def loop(self):
        if self.query is None:
            # Leave a gap of 30 seconds between query re-runs; the build queue
            # query is quite heavy and when we're at the end of a run it's
            # better to let new entries build up for a bit before we squirt them
            # into the queues rather than waste time restarting the query again
            # and again
            if datetime.utcnow() - self.timestamp > timedelta(seconds=30):
                self.query = self.db.get_build_queue()
        else:
            try:
                row = next(self.query)
                self.abi_queues[row.abi_tag].append((row.package, row.version))
            except StopIteration:
                self.query = None
                self.timestamp = datetime.utcnow()

    def handle_build(self, q):
        abi = q.recv_pyobj()
        try:
            q.send_pyobj(self.abi_queues[abi].popleft())
        except IndexError:
            q.send_pyobj(None)
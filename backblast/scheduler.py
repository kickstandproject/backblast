# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import os
import Queue
import threading


class Scheduler(threading.Thread):
    log = logging.getLogger('backblast.Scheduler')

    def __init__(self):
        self.log.debug('Preparing to initialize')
        threading.Thread.__init__(self)
        self.wake_event = threading.Event()
        self.reconfigure_complete_event = threading.Event()
        self.queue_lock = threading.Lock()
        self._exit = False
        self._pause = False
        self._reconfigure = False
        self._stopped = False
        self.launcher = None
        self.trigger_event_queue = Queue.Queue()

    def stop(self):
        self._stopped = True
        self.wake_event.set()

    def reconfigure(self, config):
        self.log.debug('Prepare to reconfigure')
        self.config = config
        self._pause = True
        self._reconfigure = True
        self.wake_event.set()
        self.log.debug('Waiting for reconfiguration')
        self.reconfigure_complete_event.wait()
        self.reconfigure_complete_event.clear()
        self.log.debug('Reconfiguration complete')

    def exit(self):
        self.log.debug('Prepare to exit')
        self._pause = True
        self._exit = True
        self.wake_event.set()
        self.log.debug('Waiting for exit')

    def run(self):
        while True:
            self.log.debug('Run handler sleeping')
            self.wake_event.wait()
            self.wake_event.clear()
            if self._stopped:
                return

            self.log.debug('Run handler awake')
            self.queue_lock.acquire()
            try:
                if not self._pause:
                    if not self.trigger_event_queue.empty():
                        self.process_event_queue()
                if self._pause:
                    self._doPauseEvent()

                if not self._pause:
                    if not self.trigger_event_queue.empty:
                        self.wake_event.set()
            except Exception:
                self.log.exception('Exception in run handler:')
            self.queue_lock.release()

    def process_event_queue(self):
        self.log.debug('Fetching trigger event')
        event = self.trigger_event_queue.get()
        self.log.debug('Processing trigger event %s' % event)
        self.addChange(event)

    def resume(self):
        self.log.debug('Resuming processing')
        self.wake_event.set()

    def _doPauseEvent(self):
        if self._exit:
            self.log.debug('Exiting')
            os._exit(0)
        if self._reconfigure:
            self.log.debug('Performing reconfiguration')
            self._pause = False
            self._reconfigure = False
            self.reconfigure_complete_event.set()

    def setLauncher(self, launcher):
        self.launcher = launcher

    def addEvent(self, event):
        if event.type is not None:
            self.log.debug('Add trigger event: %s' % event)
            self.queue_lock.acquire()
            self.trigger_event_queue.put(event)
            self.queue_lock.release()

        self.wake_event.set()

    def addChange(self, change):
        self.launchJobs(change)

    def launchJobs(self, change):
        self.launcher.launch(change)

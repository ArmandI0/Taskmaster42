import subprocess
import signal
import time
import os
import logging
from Task       import Task
from validate   import validate_task_config
from datetime   import timedelta
from _io	    import TextIOWrapper
from typing     import List
from State      import State, RUNNING_STATES, STOPPED_STATES, SIGNALLABLE_STATES

TICK_RATE = 0.5

class SimpleTask(Task):
    name: str
    cmd: list
    numprocs: int
    umask: int
    workingdir: str
    autostart: bool
    autorestart: bool
    exitcodes: list
    startretries: int
    starttime: int
    stopsignal: str
    stoptime: int
    stdout: str
    stderr: str
    env: dict
    process: subprocess.Popen
    stdout_file: TextIOWrapper
    stderr_file: TextIOWrapper
    retry: int
    comment: str
    raw_config: dict

    def __init__(self):
        raise RuntimeError("Direct instantiation not allowed, use Task.create() instead")

    @classmethod
    def _create(cls, config_dict):
        obj = cls.__new__(cls)
        obj.name = config_dict["name"]
        obj.cmd = config_dict["cmd"]
        obj.numprocs = config_dict["numprocs"]
        obj.umask = config_dict["umask"]
        obj.workingdir = config_dict["workingdir"]
        obj.autostart = config_dict["autostart"]
        obj.autorestart = config_dict["autorestart"]
        obj.exitcodes = config_dict["exitcodes"]
        obj.startretries = config_dict["startretries"]
        obj.starttime = config_dict["starttime"]
        obj.stopsignal = config_dict["stopsignal"]
        obj.stoptime = config_dict["stoptime"]
        obj.stdout = config_dict["stdout"]
        obj.stderr = config_dict["stderr"]
        obj.env = config_dict["env"]
        obj.process = None
        obj.stdout_file = None
        obj.stderr_file = None
        obj.processus_status = State.NEVER_STARTED
        obj.retry = 0
        obj.processus_time_stop = None
        obj.raw_config = None
        return obj

    @classmethod
    def create(cls, name, raw_config):
        validated = validate_task_config(name, raw_config)
        return cls._create(validated)

    def __repr__(self):
        return f"<Task {self.name}: {self.cmd}>"

    def close_redir(self):
        if self.stdout_file is not None:
            self.stdout_file.close()
            self.stdout_file = None
        if self.stderr_file is not None:
            self.stderr_file.close()
            self.stderr_file = None   

    def open_with_umask(self, path):
        umask = int(self.umask, 8)
        old_umask = os.umask(umask)

        if os.path.exists(path):
            os.remove(path)

        file = open(path, "w")
        os.umask(old_umask)
        return file

    def start(self):
        if self.processus_status in RUNNING_STATES: # If process is already started or in starting progress
            print(f"{self.name} : ERROR (already started)")
            return {"success": [], "errors": [self]}

        if self.stdout is not None:
            self.stdout_file = self.open_with_umask(self.stdout)
        if self.stderr is not None:
            self.stderr_file = self.open_with_umask(self.stderr)

        self.processus_time_start = time.time()
        self.processus_status = State.STARTING
        try:
            self.process = subprocess.Popen(self.cmd, stdout=self.stdout_file, stderr=self.stderr_file, text=True, cwd=self.workingdir, start_new_session=True)
            logging.info(f"{self.name} starting")
            return {"success": [self], "errors": []}

        except Exception as e:
            logging.error(f"{self.name} fatal : {e}")
            self.processus_status = State.FATAL
            return {"success": [], "errors": [self]}
    
    def stop(self):
        if self.processus_status in STOPPED_STATES:
            print(f"{self.name} : ERROR (not running)") 
            return {"success": [], "errors": [self]}

        signals = {
            "TERM": signal.SIGTERM,
            "KILL": signal.SIGKILL,
            "INT" : signal.SIGINT,
            "HUP" : signal.SIGHUP,
            "USR1": signal.SIGUSR1,
            "USR2": signal.SIGUSR2,
            "QUIT": signal.SIGQUIT,
        }
        sig = signals.get(self.stopsignal)
        if self.process is None:
            self.processus_status = State.STOPPED
            return {"success": [], "errors": [self]}
        self.process.send_signal(sig)
        if self.process.poll() is not None:
            self.processus_status = State.STOPPED
            logging.info(f"{self.name} stopped")
            self.close_redir()
        else:
            self.processus_time_stop = time.time()
            self.processus_status = State.STOPPING
            logging.info(f"{self.name} stopping")
        return {"success": [self], "errors": []}

    def supervise(self):
        if self.process is not None:
            poll_state = self.process.poll()
            if self.processus_status == State.STARTING:
                if poll_state is not None and poll_state not in self.exitcodes:
                    if self.retry < self.startretries:
                        self.retry += 1
                        self.processus_status = State.BACKOFF
                        logging.info(f"{self.name} backoff")
                        self.close_redir()
                    else:
                        self.processus_status = State.FATAL
                        logging.info(f"{self.name} fatal")
                        self.close_redir()
                elif time.time() - self.processus_time_start >= self.starttime:
                    self.processus_status = State.RUNNING
                    logging.info(f"{self.name} running")
            elif self.processus_status == State.BACKOFF:
                self.start()
            elif self.processus_status == State.RUNNING:
                if poll_state is not None:
                    self.close_redir()
                    if poll_state in self.exitcodes:
                        self.processus_status = State.STOPPED
                        logging.info(f"{self.name} stopped")
                    elif self.autorestart:
                        self.retry = 0
                        self.processus_status = State.BACKOFF
                        logging.info(f"{self.name} backoff")
                    else:
                        self.processus_status = State.FATAL
                        logging.info(f"{self.name} fatal")
            elif self.processus_status == State.STOPPING:
                if poll_state is not None:
                    self.close_redir()
                    self.processus_status = State.STOPPED
                    logging.info(f"{self.name} stopped")
                elif time.time() - self.processus_time_stop >= self.stoptime:
                    self.process.kill()
                    self.close_redir()
                    self.processus_status = State.STOPPED
                    logging.info(f"{self.name} stopped")


    def status(self):
        buffer = f"{self.name:<32}{self.processus_status.name:<10}"

        if self.processus_status == State.RUNNING and self.process is not None:
            uptime = timedelta(seconds=int(time.time() - self.processus_time_start))
            buffer += f"pid {self.process.pid}, uptime {uptime}"
        if self.processus_status == State.STOPPED:
            if self.processus_time_stop is not None:
                stop_time = time.strftime("%b %d %I:%M %p", time.localtime(self.processus_time_stop))
                buffer += f"{stop_time}"
            else:
                buffer += f"Not started"
        print(buffer)

    def shutdown(self):
        if self.processus_status in STOPPED_STATES:
            return {"success": [], "errors": [self]}

        if self.process is None:
            self.processus_status = State.STOPPED
            return {"success": [], "errors": [self]}

        self.process.send_signal(signal.SIGTERM)
        if self.process.poll() is not None:
            self.processus_status = State.STOPPED
            logging.info(f"{self.name} shutdown complete")
            self.close_redir()
        else:
            self.processus_time_stop = time.time()
            self.processus_status = State.STOPPING
            logging.info(f"{self.name} shutting down")
        return {"success": [self], "errors": []}
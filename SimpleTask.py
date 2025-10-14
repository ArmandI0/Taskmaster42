import subprocess
import signal
import time
import os
import logging
from Task       import Task
from validate   import validate_task_config, Autorestart
from datetime   import timedelta
from _io	    import TextIOWrapper
from State      import State, STOPPED_STATES
from Quiet		import Quiet

TICK_RATE = 0.5
BACKOFF_DELAY = 2

def	manage_print(message: str):
    print_mode = Quiet()
    if print_mode.is_enabled() == False:
        print(message)

class SimpleTask(Task):
    name: str
    cmd: list
    numprocs: int
    umask: int
    workingdir: str
    autostart: bool
    autorestart: Autorestart
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
        obj.backoff_start_time = 0
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

    def start(self):
        try:
            if self.processus_status in [State.STARTING, State.RUNNING]:
                manage_print(f"{self.name} : ERROR (already started)")
                return {"success": [], "errors": [self]}
            stdout_path = self.stdout if self.stdout is not None else os.devnull
            stderr_path = self.stderr if self.stderr is not None else os.devnull
            try:
                with open(stdout_path, "a") as stdout_file, open(stderr_path, "a") as stderr_file:
                    self.stdout_file = stdout_file
                    self.stderr_file = stderr_file

                    self.processus_time_start = time.time()
                    self.processus_status = State.STARTING

                    # To avoid modif in parent
                    def set_child_umask():
                        os.umask(int(self.umask, 8))

                    self.process = subprocess.Popen(
                        self.cmd,
                        stdout=self.stdout_file,
                        stderr=self.stderr_file,
                        text=True,
                        cwd=self.workingdir,
                        env=self.env,
                        start_new_session=True,
                        preexec_fn=set_child_umask
                    )
                    logging.info(f"{self.name} starting")
                    return {"success": [self], "errors": []}
            except (OSError, IOError, PermissionError) as e:
                logging.info(f"{self.name} fatal : {e}")
                self.processus_status = State.FATAL
                return {"success": [], "errors": [self]}
        except Exception as e:
            logging.error(f"{self.name} fatal : {e}")
            self.processus_status = State.FATAL
            return {"success": [], "errors": [self]}
    
    def stop(self):
        if self.processus_status in STOPPED_STATES:
            manage_print(f"{self.name} : ERROR (not running)") 
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
                        self.backoff_start_time = time.time()
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
                if time.time() - self.backoff_start_time >= BACKOFF_DELAY:
                    self.start()

            elif self.processus_status == State.RUNNING:
                if poll_state is not None:
                    self.close_redir()
                    
                    expected_exit = poll_state in self.exitcodes
                    
                    if expected_exit:
                        self.processus_time_stop = time.time()
                        self.processus_status = State.EXITED
                        logging.info(f"{self.name} exited")
                        
                        if self.autorestart == Autorestart.ALWAYS:
                            self.retry = 0
                            self.processus_status = State.BACKOFF
                            self.backoff_start_time = time.time()
                            logging.info(f"{self.name} backoff")
                    else:
                        if self.autorestart in [Autorestart.ALWAYS, Autorestart.UNEXPECTED]:
                            self.retry = 0
                            self.processus_status = State.BACKOFF
                            self.backoff_start_time = time.time()
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
        if self.processus_status == State.STOPPED or self.processus_status == State.EXITED:
            if self.processus_time_stop is not None:
                stop_time = time.strftime("%b %d %I:%M %p", time.localtime(self.processus_time_stop))
                buffer += f"{stop_time}"
            else:
                buffer += f"Not started"
        manage_print(buffer)

    def shutdown(self):
        if self.processus_status in STOPPED_STATES:
            return {"success": [], "errors": [self]}

        if self.process is None:
            self.processus_status = State.STOPPED
            return {"success": [], "errors": [self]}
        # Set new stoptime 
        self.stoptime = 2 
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
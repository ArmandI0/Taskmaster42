import yaml
import sys
import time
from typing     	import Dict, List
from threading  	import Lock, Event
from Task			import Task
from MultipleTask   import MultiTask
from State          import State, STOPPED_STATES 
from Quiet			import Quiet


TICK_RATE = 0.5


class Supervisor:
    def __init__(self):
        self.processus_list: Dict[str, Task] = {}
        self.lock = Lock()
        self.path_to_config = None
        self.new_processus_list: Dict[str, Task] = {}
        self.new_processus_to_start: Dict[str, Task] = {}
        self.old_processus_to_stop: List = []
        self.print_mode: Quiet = Quiet()

    def _get_task_by_full_name(self, full_name: str):
        """
            Returns the task for Multiple or Simple Task
        """
        if ":" in full_name:
            main_name, task_id = full_name.split(":", 1)
            if main_name in self.processus_list:
                task = self.processus_list[main_name]
                if isinstance(task, MultiTask):
                    return task.get_subtask(task_id)
                return None
        else:
            if full_name in self.processus_list:
                return self.processus_list[full_name]
        return None

    def load_config(self, path_to_config: str):
        try:
            with open(path_to_config, 'r') as file:
                config_data = yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Error: file '{path_to_config}' not found.")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error while parsing YAML in '{path_to_config}': {e}")
            sys.exit(1)

        if not isinstance(config_data, dict) or "programs" not in config_data:
            print("Error : configuration file must have a section 'programs:'")
            sys.exit(1)

        self.path_to_config = path_to_config

        for name, config in config_data["programs"].items():
            if ":" in name:
                print(f"Error: invalid program name '{name}'. ':' is not allowed in program names.")
                sys.exit(1)
            try:
                task = Task.create(name, config)  # Utiliser la factory
                task.raw_config = config
                self.processus_list[name] = task
            except Exception as e:
                print(f"Error in task '{name}': {e}")
                sys.exit(1)

    def start(self, processus_names: List[str] = None, all: bool = None):
        """Start and wait for processes to start"""
        waiting_list_of_starting_processus = []
        tasks_to_start = []
        
        with self.lock:
            if all:
                tasks_to_start = list(self.processus_list.values())
            else:
                for full_name in processus_names:
                    task = self._get_task_by_full_name(full_name)
                    if task is None:
                        print(f"{full_name} : ERROR (no such process)")
                    else:
                        tasks_to_start.append(task)
            
            for task in tasks_to_start:
                results = task.start()
                waiting_list_of_starting_processus.extend(results["success"])

        while waiting_list_of_starting_processus:
            with self.lock:
                for processus in waiting_list_of_starting_processus:
                    if processus.processus_status in [State.RUNNING, State.BACKOFF]:
                        print(f"{processus.name} : started")
                        waiting_list_of_starting_processus.remove(processus)
                    elif processus.processus_status in STOPPED_STATES:
                        print(f"{processus.name} : ERROR (spawn error)")
                        waiting_list_of_starting_processus.remove(processus)
            time.sleep(TICK_RATE)
        

    def stop(self, processus_names: List[str] = None, all: bool = None):
        waiting_list_of_processus_to_stop = []
        tasks_to_stop = []
        
        with self.lock:
            if all:
                tasks_to_stop = list(self.processus_list.values())
            else:
                for full_name in processus_names:
                    task = self._get_task_by_full_name(full_name)
                    if task is None:
                        print(f"{full_name} : ERROR (no such process)")
                    else:
                        tasks_to_stop.append(task)
            
            for task in tasks_to_stop:
                results = task.stop()
                waiting_list_of_processus_to_stop.extend(results["success"])

        while waiting_list_of_processus_to_stop:
            with self.lock:
                for processus in waiting_list_of_processus_to_stop:
                    if processus.processus_status in STOPPED_STATES:
                        print(f"{processus.name} : stopped")
                        waiting_list_of_processus_to_stop.remove(processus)            

    def restart(self, processus_names: List[str] = None, all: bool = None):
        self.stop(processus_names, all)
        self.start(processus_names, all)

    def reread(self):
        try:
            with open(self.path_to_config, 'r') as file:
                config_data = yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Error: Can't REREAD file '{self.path_to_config}' not found.")
            return
        except yaml.YAMLError as e:
            print(f"Error:  Can't REREAD :  while parsing YAML in '{self.path_to_config}': {e}")
            return
        
        if not isinstance(config_data, dict) or "programs" not in config_data:
            print("Error :  Can't REREAD : configuration file must have a section programs:")
            return

        with self.lock:
            modification = False
            for name, config in config_data["programs"].items():
                try:
                    if name in self.processus_list:
                        if config == self.processus_list[name].raw_config:
                            self.new_processus_list[name] = self.processus_list[name]
                        else:
                            if name not in self.old_processus_to_stop:
                                self.old_processus_to_stop.append(name)
                            task = Task.create(name, config)
                            self.new_processus_list[name] = task
                            self.new_processus_to_start[name] = task
                            self.new_processus_list[name].raw_config = config
                            self.processus_list[name].raw_config = config
                            modification = True
                            print(f"{name}: changed")
                    else:
                        task = Task.create(name, config)
                        self.new_processus_list[name] = task
                        self.new_processus_to_start[name] = task
                        modification = True
                        print(f"{name}: available")
                except Exception as e:
                    print(f"Error :  Can't REREAD : in task '{name}': {e}")
                    return
            if modification == False:
                print(f"No config updates to processes")


    def update(self):
        autostart = []
        self.print_mode.enable()
        # Stop process delete from config
        if not self.new_processus_list == {}:
            for name, processus in self.processus_list.items():
                if name not in self.new_processus_list:
                    processus.stop()

            # Stop process 
            if self.old_processus_to_stop:
                self.stop(self.old_processus_to_stop)  
 
            # Autostart of ew process
            for name, new_processus in self.new_processus_to_start.items():
                if new_processus.autostart == True:
                    autostart.append(name)
            self.processus_list = self.new_processus_list
            self.old_processus_to_stop = []
            self.new_processus_to_start = {}
            self.new_processus_list = {}
            self.start(autostart)
            self.print_mode.disable()

    def supervise(self, event: Event):
        try:
            with self.lock:
                for processus in self.processus_list.values():
                    if processus.autostart == True:
                        processus.start()
            while not event.is_set():
                with self.lock:
                    for processus in self.processus_list.values():
                        processus.supervise()
                time.sleep(TICK_RATE)
        except KeyboardInterrupt:
            return

    def status(self, processus_names: list[str] = None, all: bool = None):
        with self.lock:
            if all:
                for processus in self.processus_list.values():
                    processus.status()
            else:
                for full_name in processus_names:
                    task = self._get_task_by_full_name(full_name)
                    if task is None:
                        print(f"{full_name} : ERROR (no such process)")
                    else:
                        task.status()
    

    def shutdown(self):
        try:
            waiting_list_of_processus_to_shutdown = []
            
            with self.lock:

                for task in self.processus_list.values():
                    results = task.shutdown()
                    waiting_list_of_processus_to_shutdown.extend(results["success"])

            while waiting_list_of_processus_to_shutdown:
                with self.lock:
                    for processus in waiting_list_of_processus_to_shutdown:
                        if processus.processus_status in STOPPED_STATES:
                            waiting_list_of_processus_to_shutdown.remove(processus)
        except KeyboardInterrupt:
            # for processus in waiting_list_of_processus_to_shutdown:
            #     processus.close_redir()
            #     processus.process.kill()
            return
        
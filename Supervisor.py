import yaml
import sys
import time
from SimpleTask		import SimpleTask, State, STOPPED_STATES, RUNNING_STATES
from MultipleTask	import MultiTask
from typing     	import Dict, List, Tuple
from threading  	import Lock, Event
from Task			import Task

TICK_RATE = 0.5

class Supervisor:
    def __init__(self):
        self.processus_list: Dict[str, Task] = {}
        self.lock = Lock()
        self.path_to_config = None
        self.new_processus_list: Dict[str, Task] = {} # Quand j'update je dois regarder si les taches sont presents dans la nouvelles liste avant de les stops
        self.new_processus_to_start: Dict[str, Task] = {}
        self.old_processus_to_stop: List = []

    def _get_task_by_full_name(self, full_name: str):
        """
            Returns the task for Multiple or Simple Task
        """
        if ":" in full_name:
            main_name, subtask_name = full_name.split(":", 1)
            if main_name in self.processus_list:
                task = self.processus_list[main_name]
                if isinstance(task, MultiTask):
                    return task.get_subtask(subtask_name)
                return None
        else:
            if full_name in self.processus_list:
                return self.processus_list[full_name]
        return None

    def load_config(self, path_to_config: str):
        """
            Load Config and create Task instance for each program
        """
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
            print("Error : configuration file must have a section programs:")
            sys.exit(1)

        self.path_to_config = path_to_config
        for name, config in config_data["programs"].items():
            try:
                task = Task.create(name, config)  # Utiliser la factory
                task.raw_config = config
                self.processus_list[name] = task
            except Exception as e:
                print(f"Error in task '{name}': {e}")
                sys.exit(1)

    # Start attend que tous les programmes change d'etat RUNNING au  moins une fois pass a -> BACKOFF, FATAL ou RUNNING
    def start(self, processus_names: List[str] = None, all: bool = None):
        """Start and wait for processes to start"""
        waiting_list = []
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
                result = task.start()
                if result == 0:
                    waiting_list.extend(task.get_all_tasks())

        while waiting_list:
            with self.lock:
                for processus in waiting_list:
                    if processus.processus_status in [State.RUNNING, State.BACKOFF]:
                        print(f"{processus.name} : started")
                        waiting_list.remove(processus)
                    elif processus.processus_status in STOPPED_STATES:
                        print(f"{processus.name} : ERROR (spawn error)")
                        waiting_list.remove(processus)
            time.sleep(TICK_RATE)
        

    # la commande interagie avec les etats RUNNING STARTING et BACKOFF
    # Gerer les retours si bad processsu name dans le parsing Shell
    def stop(self, processus_names: List[str] = None, all: bool = None):
        waiting_list_of_processus_to_stop: List[Task] = []
        with self.lock:
            if all == True:
                for processus in self.processus_list.values():
                    if isinstance(processus, MultiTask): # If numprocs > 1
                        results = processus.stop()
                        for task in processus.tasks:
                            if task.name in results["success"]:
                                waiting_list_of_processus_to_stop.append(task) # Add each running task to waiting List
                    else:
                        if processus.stop() == 0: # If stop success add task to waiting List
                            waiting_list_of_processus_to_stop.append(task)   
            else:
                for full_name in processus_names:
                    processus = self._get_task_by_full_name(full_name) # Get task or subtask for call .stop method
                    if processus is None:
                        print(f"{full_name} : ERROR (no such process)")
                    if isinstance(processus, MultiTask): # If numprocs > 1
                        results = processus.stop()
                        for task in processus.tasks:
                            if task.name in results["success"]:
                                waiting_list_of_processus_to_stop.append(task) # Add each running task to waiting List
                    else:
                        if processus.stop() == 0: # If start success add task to waiting List
                            waiting_list_of_processus_to_stop.append(task)
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

        modification = False
        for name, config in config_data["programs"].items():
            try:
                if name in self.processus_list:
                    # print(f"config {config}\n raw : {self.processus_list[name].raw_config}")
                    if config == self.processus_list[name].raw_config:
                        self.new_processus_list[name] = self.processus_list[name]
                    else:
                        if name not in self.old_processus_to_stop:
                            self.old_processus_to_stop.append(name)
                        task = Task.create(name, config)
                        self.new_processus_list[name] = task
                        self.new_processus_to_start[name] = task
                        self.new_processus_list[name].raw_config = config
                        self.processus_list[name].raw_config = config       # On configure aussi la config lié au processus actuel
                        modification = True
                        print(f"{name}: changed")
                        # print(f"updated Task: {task.raw_config}")
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

        # Stop des processus supprimé dans la config
        if not self.new_processus_list == {}:
            for name, processus in self.processus_list.items():
                if name not in self.new_processus_list:
                    processus.stop()

            # Stop des processus qui qui sont supprimé de la config
            if not self.old_processus_to_stop == []:
                self.stop(self.old_processus_to_stop)

            # Autostart des nouveau processus ou process modifé
            for name, new_processus in self.new_processus_to_start.items():
                if new_processus.autostart == True:
                    autostart.append(name)
            self.processus_list = self.new_processus_list
            self.old_processus_to_stop = []
            self.new_processus_to_start = {}
            self.new_processus_list = {}

            self.start(autostart)

    def supervise(self, event: Event):
        with self.lock:
            for processus in self.processus_list.values():
                if processus.autostart == True:
                    processus.start()
        while not event.is_set():
            with self.lock:
                for processus in self.processus_list.values():
                    processus.supervise()
            time.sleep(TICK_RATE)


    def status(self, processus_names: list[str] = None, all: bool = None):
        if all:
            for processus in self.processus_list.values():
                processus.status()

    
    def shutdown(self):
        processus_to_stop: List[Task] = []
        with self.lock:
            for processus in self.processus_list.values():
                if processus.processus_status not in STOPPED_STATES:
                    processus.stop()
                    processus_to_stop.append(processus)

        while processus_to_stop:
            with self.lock:
                for processus in processus_to_stop:
                    if processus.processus_status in [State.EXITED, State.STOPPED, State.FATAL]:
                        print(f"{processus.name} : stopped")
                        processus_to_stop.remove(processus)
                    
            time.sleep(TICK_RATE)

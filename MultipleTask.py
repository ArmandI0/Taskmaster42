from Task		import Task
from SimpleTask import SimpleTask
from typing     import List

class MultiTask(Task):
    def __init__(self, name: str, raw_config: dict):
        self.name = name
        self.raw_config = raw_config
        self.autostart = raw_config["autostart"]
        self.numprocs = raw_config.get("numprocs", 1)

        self.tasks: List[SimpleTask] = []

        for i in range(self.numprocs):
            config_copy = dict(raw_config)
            task = SimpleTask.create(f"{name}:{i}", config_copy)
            self.tasks.append(task)

    def start(self) -> dict:
        # To keep return status for supervisor
        results = {
            "success": [],
            "errors": []
        }
        for task in self.tasks:
            result = task.start()
            # Register return value for the Supervisor part
            if result == 0:
                results["success"].append(task.name) 
            else:
                results["errors"].append(task.name)
        if results["success"]:
            return 0
        else:
            return 1

    def stop(self):
        results = {
            "success": [],
            "errors": []
        }
        for task in self.tasks:
            result = task.stop()
            if result == 0:
                results["success"].append(task.name) 
            else:
                results["errors"].append(task.name)
        return results

    def supervise(self):
        for task in self.tasks:
            task.supervise()

    def status(self):
        for task in self.tasks:
            task.status()

    def get_subtask(self, task_id: str) -> SimpleTask:
        for task in self.tasks:
            main_name, task_id_subtask = task.name.split(":", 1)
            if task_id_subtask == task_id:
                return task
        return None

    def get_subtask_names(self) -> List[str]:
        return [task.name for task in self.tasks]

    def get_all_tasks(self) -> List[SimpleTask]:
        return self.tasks
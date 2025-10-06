from Task		import Task
from SimpleTask import SimpleTask
from typing import List

class MultiTask(Task):
    def __init__(self, name: str, raw_config: dict):
        self.name = name
        self.raw_config = raw_config
        self.autostart = raw_config["autostart"]
        self.numprocs = raw_config.get("numprocs", 1)

        self.tasks: List[SimpleTask] = []

        for i in range(self.numprocs):
            config_copy = dict(raw_config)
            config_copy["name"] = f"{name}_{i}"
            task = SimpleTask.create(config_copy["name"], config_copy)
            self.tasks.append(task)

    def start(self) -> dict:
        # To keep return status for supervisor
        results = {
            "success": [],
            "errors": []
        }
        for task in self.tasks:
            result = task.start()
            if result == 0:
                results["success"].append(task.name)
            else:
                results["errors"].append(task.name)
        return results

    def stop(self):
        for task in self.tasks:
            task.stop()

    def supervise(self):
        for task in self.tasks:
            task.supervise()

    def status(self):
        return "\n".join(task.status() for task in self.tasks)

    def get_subtask(self, subtask_name: str) -> SimpleTask:
        for task in self.tasks:
            if task.name == subtask_name:
                return task
        return None

    def get_subtask_names(self) -> List[str]:
        return [task.name for task in self.tasks]

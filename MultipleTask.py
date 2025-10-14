from Task		import Task
from SimpleTask import SimpleTask
from typing     import List

class MultiTask(Task):
    def __init__(self, name: str, raw_config: dict):
        self.name = name
        self.raw_config = raw_config
        self.numprocs = raw_config.get("numprocs", 1)
        self.tasks: List[SimpleTask] = []

        for i in range(self.numprocs):
            config_copy = dict(raw_config)
            task = SimpleTask.create(f"{name}:{i}", config_copy)
            if i == 0:
                self.autostart = task.autostart
            self.tasks.append(task)

    def start(self) -> dict:
        # To keep return status for supervisor
        results = {
            "success": [],
            "errors": []
        }
        for task in self.tasks:
            result = task.start()
            results["success"].extend(result["success"])
            results["errors"].extend(result["errors"])
        return results

    def stop(self):
        results = {
            "success": [],
            "errors": []
        }
        for task in self.tasks:
            result = task.stop()
            results["success"].extend(result["success"])
            results["errors"].extend(result["errors"])
        return results

    def supervise(self):
        for task in self.tasks:
            task.supervise()

    def status(self):
        for task in self.tasks:
            task.status()

    def shutdown(self):
        results = {
            "success": [],
            "errors": []
        }
        for task in self.tasks:
            result = task.shutdown()
            results["success"].extend(result["success"])
            results["errors"].extend(result["errors"])
        return results

    def get_subtask(self, task_id: str) -> SimpleTask:
        for task in self.tasks:
            main_name, task_id_subtask = task.name.split(":", 1)
            if task_id_subtask == task_id:
                return task
        return None

    def get_subtask_names(self) -> List[str]:
        return [task.name for task in self.tasks]

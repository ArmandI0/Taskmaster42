class MultiTask:
    def __init__(self, name: str, raw_config: dict):
        self.name = name
        self.raw_config = raw_config
        self.numprocs = raw_config.get("numprocs", 1)

        self.tasks = []

        for i in range(self.numprocs):
            config_copy = dict(raw_config)
            config_copy["name"] = f"{name}_{i}"
            task = Task.create(config_copy["name"], config_copy)
            self.tasks.append(task)

    def start(self):
        for task in self.tasks:
            task.start()

    def stop(self):
        for task in self.tasks:
            task.stop()

    def supervise(self):
        for task in self.tasks:
            task.supervise()

    def status(self):
        return "\n".join(task.status() for task in self.tasks)

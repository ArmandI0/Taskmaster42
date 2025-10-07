from abc            import ABC, abstractmethod

class Task(ABC):
    """Abstract Method for Multiple and Simple Task"""
    
    @staticmethod
    def create(name: str, raw_config: dict):
        # Import in method to avoid circular inclusion
        from MultipleTask   import MultiTask
        from SimpleTask     import SimpleTask
        numprocs = raw_config.get("numprocs", 1)
        if numprocs > 1:
            return MultiTask(name, raw_config)
        else:
            return SimpleTask.create(name, raw_config)
    
    @abstractmethod
    def start(self): pass
    
    @abstractmethod
    def stop(self): pass
    
    @abstractmethod
    def supervise(self): pass
    
    @abstractmethod
    def status(self): pass
    
    @abstractmethod
    def get_all_tasks(self): pass
from abc            import ABC, abstractmethod
from validate       import validate_numprocs

class Task(ABC):
    """Abstract Method for Multiple and Simple Task"""
    
    @staticmethod
    def create(name: str, raw_config: dict):
        # Import in method to avoid circular inclusion
        from MultipleTask   import MultiTask
        from SimpleTask     import SimpleTask
        numprocs = validate_numprocs(name, raw_config)
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
    def shutdown(self): pass

from abc import ABC, abstractmethod

class Task(ABC):
    """
        Abstract Method for Multiple and Simple Task
    """

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def supervise(self):
        pass

    @abstractmethod
    def status(self):
        pass

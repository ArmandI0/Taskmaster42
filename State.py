from enum 	    import Enum, auto

class State(Enum):
    STARTING = auto()
    RUNNING = auto()
    BACKOFF = auto()
    FATAL = auto()
    EXITED = auto()
    STOPPED = auto()
    STOPPING = auto()
    UNKNOWN = auto()
    NEVER_STARTED = auto()

STOPPED_STATES = (
    State.STOPPED,
    State.EXITED,
    State.FATAL,
    State.UNKNOWN,
    State.NEVER_STARTED,
)

RUNNING_STATES = (
    State.RUNNING,
    State.BACKOFF,
    State.STARTING,
)

SIGNALLABLE_STATES = (
    State.RUNNING,
    State.STARTING,
    State.STOPPING,
)

import signal
from Supervisor import Supervisor
from threading import Event
import readline
import sys

COMMANDS = ["status", "start", "stop", "restart", "reread", "update", "shutdown", "help"]

sighup_event = Event()

def completer(text, state):
    options = [cmd for cmd in COMMANDS if cmd.startswith(text)]
    if state < len(options):
        return options[state]
    return None

def print_no_args_command(command_name: str):
    print(f"""{command_name}: {command_name} requires a process name
    {command_name} <name>          Stop a process
    {command_name} <name> <name>   Stop multiple processes or groups
    {command_name} all             Stop all processes
    """)

def run_shell(taskmaster: Supervisor, event: Event):
    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")
    readline.set_history_length(1000)

    def handle_sigquit(signum, frame):
        raise EOFError

    def handle_sighup(signum, frame):
        print("\n[!] SIGHUP received → rereading config")
        taskmaster.reread()
        print("taskmaster > ", end="", flush=True)

    signal.signal(signal.SIGQUIT, handle_sigquit)
    signal.signal(signal.SIGHUP, handle_sighup)

    while not event.is_set():
        try:
            user_input = input("taskmaster > ").strip()
            if not user_input:
                continue

            if sighup_event.is_set():
                sighup_event.clear()
                taskmaster.reread()
                continue 

            args = user_input.split()
            command = args[0]
            params = args[1:]

            commands_with_args = ["start", "stop", "restart", "status"]
            if command in commands_with_args and not params:
                print_no_args_command(command)
                continue

            match command:
                case "help":
                    print("""Available commands:
  - status [<name1> <name2> ...] | all
  - start [<name1> <name2> ...] | all
  - stop [<name1> <name2> ...] | all
  - restart [<name1> <name2> ...] | all
  - reread
  - update
  - shutdown
  - help
                    """)

                case "status":
                    if "all" in params:
                        taskmaster.status(all=True)
                    else:
                        taskmaster.status(processus_names=params)

                case "start":
                    if "all" in params:
                        taskmaster.start(all=True)
                    else:
                        taskmaster.start(processus_names=params)

                case "stop":
                    if "all" in params:
                        taskmaster.stop(all=True)
                    else:
                        taskmaster.stop(processus_names=params)

                case "restart":
                    if "all" in params:
                        taskmaster.restart(all=True)
                    else:
                        taskmaster.restart(processus_names=params)

                case "reread":
                    taskmaster.reread()

                case "update":
                    taskmaster.update()

                case "shutdown":
                    print("Shutting down...")
                    taskmaster.shutdown()
                    event.set()

                case _:
                    print(f"Unknown command: {command}")

        except KeyboardInterrupt:
            print("")
            continue
        except EOFError:
            print("\n[!] Caught Ctrl+D or SIGQUIT → shutting down...")
            taskmaster.shutdown()
            event.set()
            break
        except Exception as e:
            print(f"Error: {e}")

import argparse
from Supervisor import Supervisor
from shell import run_shell
from threading import Thread, Event
import logging
import sys

def main(args):
    try:
        stop_event = Event()

        taskmaster = Supervisor()
        taskmaster.load_config(args)
        try:
            logging.basicConfig(
                filename="/tmp/taskmaster.log",
                level=logging.INFO,
                format="%(asctime)s - %(levelname)s - %(message)s"
            )
        except Exception as e:
            print(f"Logging file error : {e}", file=sys.stderr)
            sys.exit(1) 

        monitoring = Thread(target=taskmaster.supervise, args=(stop_event,))
        monitoring.start()
        run_shell(taskmaster, stop_event)
        monitoring.join()
    except OSError as e:
        print(f"Open failed : {e}")
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Taskmaster")
    parser.add_argument("-c", "--config", required=True, help="Path to config file.yml")
    args = parser.parse_args()
    main(args.config)

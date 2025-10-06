import os
import signal

def validate_task_config(name, config):
    validated_env = validate_env(name, config, {})
    merged_env = {**os.environ, **validated_env}

    return {
        "name": validate_name(name, config),
        "cmd": validate_cmd(name, config),
        "numprocs": validate_numprocs(name, config, 1),
        "umask": validate_umask(name, config, "022"),
        "workingdir": validate_workingdir(name, config, os.getcwd()),
        "autostart": validate_autostart(name, config, True),
        "autorestart": validate_autorestart(name, config, False),
        "exitcodes": validate_exitcodes(name, config, [0]),
        "startretries": validate_positive_int(name, config, "startretries", 3),
        "starttime": validate_positive_int(name, config, "starttime", 1),
        "stopsignal": validate_stopsignal(name, config, "TERM"),
        "stoptime": validate_positive_int(name, config, "stoptime", 10),
        "stdout": validate_output_file(name, config, "stdout"),
        "stderr": validate_output_file(name, config, "stderr"),
        "env": merged_env,
    }

def err(name, msg):
    raise ValueError(f"Task '{name}': {msg}")

def validate_name(name, config):
    if not isinstance(name, str) or not name.strip() or name.strip() == "all":
        err(name, "'name' is required and must be a non-empty string. Banned name: 'all'.")
    return name.strip()

def validate_cmd(name, config):
    cmd = config.get("cmd")
    if not isinstance(cmd, str) or not cmd.strip():
        err(name, "'cmd' is required and must be a non-empty string.")
    return cmd.strip().split()

def validate_numprocs(name, config, default):
    numprocs = config.get("numprocs", default)
    if not isinstance(numprocs, int) or numprocs < 1:
        err(name, "'numprocs' must be a positive integer.")
    return numprocs

def validate_umask(name, config, default):
    umask = config.get("umask", default)
    if not isinstance(umask, str) or not umask.strip():
        err(name, "umask must be a non-empty string like '022'")
    if not umask.isdigit() or len(umask) not in (3, 4):
        err(name, "umask must be a string of 3 or 4 digits like '022'")
    for digit in umask:
        if digit not in "01234567":
            err(name, f"invalid umask digit '{digit}' in '{umask}'")
    return umask

def validate_workingdir(name, config, default):
    workingdir = config.get("workingdir", default)
    if not isinstance(workingdir, str):
        err(name, "'workingdir' must be a string.")
    if not os.path.isdir(workingdir):
        err(name, f"'workingdir' path '{workingdir}' does not exist or is not a directory.")
    if not os.access(workingdir, os.W_OK):
        err(name, f"'workingdir' path '{workingdir}' is not writable.")
    return workingdir

def validate_autostart(name, config, default):
    autostart = config.get("autostart", default)
    if not isinstance(autostart, bool):
        err(name, "'autostart' must be a boolean.")
    return autostart

def validate_autorestart(name, config, default):
    autorestart = config.get("autorestart", default)
    if not isinstance(autorestart, bool):
        err(name, "'autorestart' must be a boolean.")
    return autorestart

def validate_exitcodes(name, config, default):
    exitcodes = config.get("exitcodes", default)
    if isinstance(exitcodes, int):
        exitcodes = [exitcodes]
    if not isinstance(exitcodes, list) or not all(isinstance(c, int) and 0 <= c <= 255 for c in exitcodes):
        err(name, "'exitcodes' must be list of ints between 0 and 255.")
    return exitcodes

def validate_positive_int(name, config, key, default):
    val = config.get(key, default)
    if not isinstance(val, int) or val < 0:
        err(name, f"'{key}' must be a non-negative integer.")
    return val

def validate_stopsignal(name, config, default):
    stopsignal = config.get("stopsignal", default)
    valid_signals = {sig[3:] for sig in dir(signal) if sig.startswith("SIG") and not sig.startswith("SIG_")}
    if stopsignal not in valid_signals:
        err(name, f"'stopsignal' must be a valid signal name like TERM, INT, USR1 (got '{stopsignal}')")
    return stopsignal

def validate_output_file(name, config, key):
    path = config.get(key)
    if not path:
        return None
    if not isinstance(path, str):
        err(name, f"'{key}' must be a string.")
    try:
        with open(path, "a"):
            pass
    except Exception as e:
        err(name, f"'{key}' path '{path}' is not writable or cannot be created: {e}")
    return path

def validate_env(name, config, default):
    env = config.get("env", default)
    if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        err(name, "'env' must be a dictionary of string:string.")
    return env

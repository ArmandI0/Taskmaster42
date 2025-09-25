## Usage

```bash
python3 taskmaster.py -c config.yml
```

## Notes

## Commande a implementer

## CONFIG :

```Yml
cmd: "/usr/bin/echo coucou"           # pas de valeur par défaut → obligatoire
numprocs: 1                           # défaut: 1
umask: 022                            # défaut: 022
workingdir: /tmp                      # défaut: (repertoire actuel)
autostart: true                       # défaut: true
autorestart: never                    # défaut: unexpected (valeurs possibles: true, false, unexpected)
exitcodes: [0, 1]                     # défaut: [0]
startretries: 2                       # défaut: 3
starttime: 1                          # défaut: 1
stopsignal: TERM                      # défaut: TERM
stoptime: 6                           # défaut: 10
stdout: /tmp/stdout_echo              # défaut: None (stdout non redirigé si absent)
stderr: /tmp/stderr_echo              # défaut: None (non redirige si absent)

```

## start :

### parametres a prendre en compte 
startretries : defini le -nombre de retry si echec aux demarage
starttime : temps mini pendant lequel le processus doit rester en vie
autostart : si autostart = false ne pas lancer le programme au debut
faire les redirections dans starts
stdout:
stderr: 

### state
la commande start ne relance pas start si le status est 
```
    RUNNING -> test1: ERROR (already started)
    BACKOFF
    STARTING
```



```
start <name>		Start a process
start <name> <name>	Start multiple processes or groups
start all		Start all processes
```

## restart :

```
    restart <name>		    Restart a process
    restart <name> <name>	Restart multiple processes or groups
    restart all		        Restart all processes

    Note: restart does not reread config files. For that, see reread and update.
```

## stop (all a executer dans un thread):
type de signals
```
HUP
INT
QUIT
KILL
TERM
USR1
USR2
WINCH
```

Pour faire un stop supervisor envoie la variable de stopsignal et kill les processus si pas stoppe au bout du wait.

Quand on fait stop all ca envoie tous les signals et w

## status :

- reload
- shutdown


| État       | Signification                                                                  | Quand ça arrive                                                                 |
| ---------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `STARTING` | Le processus vient d’être lancé, et `supervisord` attend `startsecs` secondes  | Juste après un `start`, tant que `startsecs` n’est pas dépassé                  |
| `RUNNING`  | Le processus a survécu au moins `startsecs` secondes, il est considéré stable  | Démarrage réussi                                                                |
| `BACKOFF`  | Le processus est mort trop tôt, Supervisor attend avant une nouvelle tentative | Échec de démarrage, Supervisor va encore réessayer (`startretries` pas dépassé) |
| `FATAL`    | Le processus a échoué à démarrer après `startretries` tentatives               | Tous les retries ont échoué → Supervisor abandonne                              |
| `EXITED`   | Le processus s’est arrêté (normalement ou non), mais n’était pas censé         | Ex : `autorestart=false` et le process termine                                  |
| `STOPPED`  | Le processus a été arrêté manuellement ou par une autre directive              | Via `supervisorctl stop` ou arrêt programmé                                     |
| `STOPPING` | Le processus est en train d’être stoppé                                        | Phase de transition vers `STOPPED`                                              |
| `UNKNOWN`  | État indéterminé, Supervisor n’arrive pas à récupérer les infos                | Fichier `pid` manquant, crash, corruption, etc.                                 |
| `NEVER_STARTED`  | Le processus n'a jamais ete demarrer                | autostart a FALSE et aucun demarrage manuel                                 |

## umask:

Le umask est un masque binaire qui désactive certaines permissions. Chaque chiffre octal correspond à :

Chiffre	Permissions désactivées
| Chiffre | Permissions désactivées |
| ------- | ----------------------- |
| 0       | aucune                  |
| 1       | --x                     |
| 2       | -w-                     |
| 3       | -wx                     |
| 4       | r--                     |
| 5       | r-x                     |
| 6       | rw-                     |
| 7       | rwx                     |

example:

| Umask | Permissions fichier créés (666 & \~umask) |
| ----- | ----------------------------------------- |
| 000   | rw-rw-rw-                                 |
| 022   | rw-r--r--                                 |
| 027   | rw-r-----                                 |
| 077   | rw-------                                 |


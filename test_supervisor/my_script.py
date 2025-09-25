import signal
import time

def handle_hup(signum, frame):
    print("Reçu SIGHUP, mais je continue...")

signal.signal(signal.SIGHUP, handle_hup)

try:
    while True:
        print("Je tourne en boucle...")
        time.sleep(1)

except KeyboardInterrupt:
    print("Arrêt demandé, je quitte proprement.")
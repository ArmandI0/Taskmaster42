import os
import random
import string

random_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

os.makedirs("generatedFiles", exist_ok=True)
# Définir le chemin complet du fichier
filename = os.path.join("generateFiles", f"file_{random_id}.txt")

with open(filename, "w") as f:
    f.write("Ceci est un fichier avec un ID aléatoire.\n")

print(f"Fichier créé : {filename}")

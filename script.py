import re
import shutil
import sys

path = "frontend/src/App.js"
shutil.copyfile(path, path + ".bak")

with open(path, encoding="utf-8", newline="") as f:
    s = f.read()
avant = len(s)

# 1. Doublon <div setting-group> + <Volume2> juste avant {!audioUnlocked ...
s = re.sub(
    r'(?:<div className="setting-group">\s*)?'
    r'(?:<Volume2 size={16} className="setting-icon" />\s*)?'
    r'(?=\{!audioUnlocked)',
    "", s, count=1)
print("doublon supprimé" if len(s) != avant else "pas de doublon trouvé")

# 2. Fin du bloc vitesse : on garde jusqu'à son </div>, puis fermeture propre
i = s.find("{s}x</SelectItem>)}")
if i < 0:
    sys.exit("repère du sélecteur de vitesse introuvable : rien modifié")
for tag in ("</SelectContent>", "</Select>", "</div>"):
    i = s.find(tag, i)
    if i < 0:
        sys.exit(f"{tag} introuvable après le sélecteur de vitesse : rien modifié")
    i += len(tag)
s = s[:i] + "\n        </div>\n      </div>\n    </div>\n  );\n}\n"

# 3. Vérifications
print("<div :", len(re.findall(r"<div\b", s)), "| </div> :", len(re.findall(r"</div>", s)))
print("<Select> :", len(re.findall(r"<Select\b", s)), "| </Select> :", len(re.findall(r"</Select>", s)))

with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(s)
print("--- fin du fichier ---")
print("\n".join(s.splitlines()[-8:]))

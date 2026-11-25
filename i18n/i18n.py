"""Equivalent Windows du Makefile de traduction.

Usage (OSGeo4W Shell, depuis n'importe quel dossier) :
    python i18n.py update     # extrait les chaines dans les .ts
    python i18n.py release    # compile les .ts en .qm
    python i18n.py tools      # affiche seulement les outils trouves
"""
import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TOOL = "LightPollutionToolbox"
LANGS = ["en", "fr"]
# Langues dont la traduction est le texte source (les chaines du code sont en anglais)
SOURCE_AS_TRANSLATION = ["en"]

HERE = Path(__file__).resolve().parent      # dossier i18n
SOURCES_ROOT = HERE.parent                  # comme `find ..` du Makefile
EXCLUDED_DIRS = {"venv", ".venv", "site-packages", "__pycache__", ".git"}

# Noms d'executables testes, par ordre de preference
LUPDATE_NAMES = ["pylupdate5", "pylupdate6", "pyside6-lupdate"]
LRELEASE_NAMES = ["lrelease", "lrelease-qt5", "lrelease-qt6", "pyside6-lrelease"]


def search_dirs():
    """Dossiers ou chercher en plus du PATH (installation OSGeo4W / QGIS)."""
    roots = []
    if os.environ.get("OSGEO4W_ROOT"):          # defini par l'OSGeo4W Shell
        roots.append(Path(os.environ["OSGEO4W_ROOT"]))
    roots += [Path(r"C:\OSGeo4W"), Path(r"C:\OSGeo4W64")]
    roots += [Path(p) for p in glob.glob(r"C:\Program Files\QGIS*")]

    dirs = [Path(sys.executable).parent, Path(sys.executable).parent / "Scripts"]
    for root in roots:
        if not root.exists():
            continue
        dirs += [root / "bin"]
        for pattern in ("apps/*/bin", "apps/Python*/Scripts", "apps/Qt*/bin"):
            dirs += [Path(p) for p in glob.glob(str(root / pattern))]
    return [d for d in dirs if d.is_dir()]


def find_tool(names):
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    for d in search_dirs():
        for name in names:
            for ext in (".exe", ".bat", ".cmd", ""):
                candidate = d / (name + ext)
                if candidate.is_file():
                    return str(candidate)
    return None


def run(exe, args, quiet=False):
    cmd = [exe] + args
    if exe.lower().endswith((".bat", ".cmd")):
        cmd = ["cmd", "/c"] + cmd
    line = " ".join(cmd)
    if len(line) > 30000:
        print("Attention : ligne de commande tres longue (%d caracteres)" % len(line))
    print(line if not quiet else "%s ... (%d fichiers) -ts %s" % (exe, len(args) - 2, args[-1]))
    return subprocess.call(cmd, cwd=str(HERE))


def python_sources():
    files = []
    for path in SOURCES_ROOT.rglob("*.py"):
        if EXCLUDED_DIRS.intersection(path.parts):
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        files.append(path)
    return sorted(files)


def rel(path):
    """Chemin relatif au dossier i18n (plus court, evite la limite de ligne de commande)."""
    try:
        return os.path.relpath(str(path), str(HERE))
    except ValueError:  # autre lecteur
        return str(path)


def update(lupdate):
    sources = [rel(p) for p in python_sources()]
    code = 0
    for lang in LANGS:
        ts = "%s_%s.ts" % (TOOL, lang)
        # comme le Makefile : tous les .py en arguments, un appel par langue
        code = run(lupdate, sources + ["-ts", ts], quiet=True) or code
        if lang in SOURCE_AS_TRANSLATION and (HERE / ts).is_file():
            fill_with_source(HERE / ts)
    return code


def fill_with_source(ts_path):
    """Copie le texte source dans les traductions vides d'un .ts.

    Les traductions deja renseignees ne sont jamais modifiees.
    Le texte est recopie tel quel (deja echappe en XML), la mise en forme du fichier est conservee.
    """
    with open(ts_path, encoding="utf-8", newline="") as f:
        content = f.read()
    count = [0]

    def fix_message(match):
        block = match.group(0)
        src = re.search(r"<source>(.*?)</source>", block, re.S)
        if not src or not src.group(1):
            return block
        text = src.group(1)
        # traductions "vanished"/"obsolete" : on ne touche pas
        if re.search(r'<translation type="(vanished|obsolete)"', block):
            return block
        new = block
        # message simple : <translation type="unfinished"></translation> (ou version vide / auto-fermante)
        new = re.sub(r'<translation(?: type="unfinished")?\s*(?:/>|>\s*</translation>)',
                     lambda m: "<translation>%s</translation>" % text, new)
        # message avec formes plurielles
        if "<numerusform" in new:
            new = re.sub(r"<numerusform\s*(?:/>|>\s*</numerusform>)",
                         lambda m: "<numerusform>%s</numerusform>" % text, new)
            if "<numerusform></numerusform>" not in new:
                new = new.replace('<translation type="unfinished">', "<translation>")
        if new != block:
            count[0] += 1
        return new

    content = re.sub(r"<message\b.*?</message>", fix_message, content, flags=re.S)
    with open(ts_path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    print("%s : %d traductions remplies avec le texte source" % (os.path.basename(ts_path), count[0]))


def release(lrelease):
    code = 0
    for lang in LANGS:
        ts = "%s_%s.ts" % (TOOL, lang)
        qm = "%s_%s.qm" % (TOOL, lang)
        code = run(lrelease, [ts, "-qm", qm]) or code
    return code


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action not in ("update", "release", "tools"):
        print(__doc__)
        return 1

    lupdate = find_tool(LUPDATE_NAMES)
    lrelease = find_tool(LRELEASE_NAMES)
    print("lupdate  :", lupdate or "INTROUVABLE")
    print("lrelease :", lrelease or "INTROUVABLE")
    if action == "tools":
        return 0

    tool = lupdate if action == "update" else lrelease
    if not tool:
        print("\nOutil introuvable. Installe PySide6 (pip install pyside6) ou "
              "ajoute le dossier de l'outil au PATH.")
        return 1
    return update(tool) if action == "update" else release(tool)


if __name__ == "__main__":
    sys.exit(main())

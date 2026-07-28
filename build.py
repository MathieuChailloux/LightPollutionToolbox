from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT_DIR = Path(__file__).resolve().parent

PLUGINNAME = "LightPollutionToolbox"
ARCHIVE_DIR = ROOT_DIR / PLUGINNAME
ARCHIVE_NAME = f"{PLUGINNAME}.zip"
ARCHIVE_PATH = ROOT_DIR / ARCHIVE_NAME

TO_COPY_DIRS = [
    "algs",
    "help",
    "i18n",
    "icons",
    "qgis_lib"
]

def remove(path):
    print("remove {}".format(path))
    path = Path(path)
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()

# Nettoyage
remove(ARCHIVE_DIR)
remove(ARCHIVE_PATH)

ARCHIVE_DIR.mkdir()

# Copie des dossiers
for d in TO_COPY_DIRS:
    shutil.copytree(ROOT_DIR / d, ARCHIVE_DIR / d)

# Suppression des fichiers __pycache__
for f in ARCHIVE_DIR.rglob("__pycache__"):
    print("pycache {}".format(f))
    remove(ARCHIVE_DIR / f)
    
# Suppression fichiers inutiles
remove(ARCHIVE_DIR / "help" / "make.bat")

# Copie des fichiers racine
for f in Path(ROOT_DIR).glob("*.py"):
    print("Copy file {}".format(f))
    if f.name != "build.py":
        print("Copy file {}".format(ROOT_DIR / f))
        shutil.copy2(ROOT_DIR / f, ARCHIVE_DIR)

for f in Path(ROOT_DIR).glob("*.md"):
    shutil.copy2(ROOT_DIR / f, ARCHIVE_DIR)

shutil.copy2(ROOT_DIR / "LICENSE", ARCHIVE_DIR)
shutil.copy2(ROOT_DIR / "metadata.txt", ARCHIVE_DIR)
shutil.copy2(ROOT_DIR / "requirements.txt", ARCHIVE_DIR)
shutil.copy2(ROOT_DIR / "lamp.png", ARCHIVE_DIR)

## git_hash function
def git_hash(repo_path=ROOT_DIR):
    repo = Path(repo_path).resolve()
    git = repo / ".git"
    if not git.exists():
        raise FileNotFoundError(f"{repo} n'est pas un dépôt Git")
    # Cas d'un sous-module : .git est un fichier contenant
    # "gitdir: ../.git/modules/..."
    if git.is_file():
        line = git.read_text(encoding="utf-8").strip()
        if not line.startswith("gitdir:"):
            raise RuntimeError(f"Format de {git} inconnu")
        git_dir = (repo / line[7:].strip()).resolve()
    else:
        git_dir = git

    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()

    # HEAD détachée : contient directement le hash
    if not head.startswith("ref:"):
        return head

    # HEAD pointe vers une référence
    ref = head[5:].strip()
    ref_file = git_dir / ref

    if ref_file.exists():
        return ref_file.read_text(encoding="utf-8").strip()

    # Dernier recours : chercher dans packed-refs
    packed_refs = git_dir / "packed-refs"
    if packed_refs.exists():
        with packed_refs.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or line.startswith("^"):
                    continue
                sha, name = line.split(" ", 1)
                if name == ref:
                    return sha

    raise RuntimeError(f"Impossible de trouver la référence {ref}")

# git-versions.txt
with open(ARCHIVE_DIR / "git-versions.txt", "w") as fp:
    fp.write(f"{PLUGINNAME} commit number\n")
    gh = git_hash()
    print("gh = {}".format(gh))
    # gh_lib = git_hash(LIB_DIR)
    # print("gh_lib = {}".format(gh_lib))
    fp.write(gh + "\n\n")
    # fp.write("qgis_lib_mc commit number\n")
    # fp.write(gh_lib + "\n\n")

# Création du zip
with zipfile.ZipFile(ARCHIVE_PATH, "w", zipfile.ZIP_DEFLATED) as z:
    for p in ARCHIVE_DIR.rglob("*"):
        z.write(p, p.relative_to(ROOT_DIR))

shutil.rmtree(ARCHIVE_DIR)

print(f"{ARCHIVE_PATH} créé.")

# BUILD plugins.xml

def read_metadata(path):
    metadata = {}

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            metadata[key.strip()] = value.strip()

    return metadata

metadata = read_metadata(ROOT_DIR / "metadata.txt")

version = metadata["version"]
name = metadata["name"]
description = metadata.get("description", "")
qgis_minimum_version = metadata.get("qgisMinimumVersion", "3.0")


download_url = (
    f"https://github.com/MathieuChailloux/MitiConnect/releases/download/"
    f"v{version}/{ARCHIVE_NAME}"
)

plugins_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<plugins>
  <pyqgis_plugin name="{name}">
    <version>{version}</version>
    <description>{description}</description>
    <qgis_minimum_version>{qgis_minimum_version}</qgis_minimum_version>
    <icon>icons/icon.png</icon>
    <author_name>Mathieu Chailloux</author_name>
    <homepage>https://github.com/MathieuChailloux/MitiConnect</homepage>
    <download_url>{download_url}</download_url>
  </pyqgis_plugin>
</plugins>
"""

with open(ROOT_DIR / "plugins.xml", "w", encoding="utf-8") as f:
    f.write(plugins_xml)
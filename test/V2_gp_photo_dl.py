"""
=== GoPro HERO7 Black – Guide de contrôle Python ===
Connexion réalisée avec la lib goprocam (GoProCamera, constants).

📌 Distinction des IDs :
- ✅ Confirmé = testé et validé en live avec ta HERO7 Black
- ⚠️ À vérifier = trouvé dans la doc/SDK GoPro ou forums, mais pas validé chez toi
                  → peut varier selon firmware ou modèle

----------------------------------------
✅ STATUS (confirmés)
----------------------------------------
- status[2]  : Mode actuel (0=Vidéo, 1=Photo, 2=Timelapse)
- status[8]  : Enregistrement en cours (0=Stop, 1=Recording)
- status[34] : Nombre de photos restantes sur la carte
- status[35] : Nombre de vidéos restantes sur la carte
- status[61] : Niveau de batterie (%)
- status[30] : Numéro de série
- status[37] : Résolution vidéo (4 = 1080p, autres valeurs à mapper)
- status[39] : Champ de vision (FOV)
- status[57] : Espace utilisé (en Ko ?)
- status[60] : Taille mémoire totale (MB)
- status[64] : Espace libre (MB)

----------------------------------------
⚠️ STATUS (à vérifier)
----------------------------------------
- status[1]  : Mode général (souvent 1=Video, 2=Photo, 3=Timelapse)
- status[4]  : Valeur spéciale (souvent 255 quand non défini)
- status[43–49] : Réglages réseau / streaming (non confirmés)
- status[70–73] : Horloge de la GoPro (heures/minutes/secondes)

----------------------------------------
✅ SETTINGS (confirmés)
----------------------------------------
- settings[17] : Nombre de mégapixels photo
- settings[26] : Résolution vidéo (ex: 4 = 1080p)
- settings[29] : Mode rafale photo
- settings[30] : Intervalle timelapse
- settings[32] : FPS (frames per second)
- settings[84] : Bitrate vidéo (6=High, etc.)

----------------------------------------
⚠️ SETTINGS (à vérifier)
----------------------------------------
- settings[2]  : Orientation (Up/Down/Auto)
- settings[41/42/44/45] : White balance (balance des blancs)
- settings[47] : Netteté (sharpness)
- settings[48] : EV Comp (exposition)
- settings[59] : Hypersmooth (stabilisation électronique)
- settings[80] : Protune On/Off
- settings[81–85] : Paramètres Protune avancés (ISO min/max, etc.)

----------------------------------------
📸 Commandes testées avec succès
----------------------------------------
- gopro.shutter("on")  → démarre enregistrement vidéo
- gopro.shutter("off") → stop enregistrement
- gopro.take_photo()   → prend une photo (en mode photo)
  ⚠️ Nécessite : gopro.mode(constants.Mode.PhotoMode, constants.Mode.SubMode.Photo.Single)

----------------------------------------
🛠 Conseils
----------------------------------------
- Pour explorer : status = gopro.getStatus(constants.Status.Status, id)
                  settings = gopro.getStatus(constants.Status.Settings, id)
- Affiche le JSON brut pour voir tous les IDs disponibles.
- Ajoute toi-même les traductions quand tu confirmes un ID.
"""


"""
=== GoPro HERO7 Black – Guide de contrôle Python ===
Connexion réalisée avec la lib goprocam (GoProCamera, constants).

📌 Distinction des IDs :
- ✅ Confirmé = testé et validé en live avec ta HERO7 Black
- ⚠️ À vérifier = trouvé dans la doc/SDK GoPro ou forums, mais pas validé chez toi
                  → peut varier selon firmware ou modèle

----------------------------------------
✅ STATUS (confirmés)
----------------------------------------
- status[2]  : Mode actuel (0=Vidéo, 1=Photo, 2=Timelapse)
- status[8]  : Enregistrement en cours (0=Stop, 1=Recording)
- status[34] : Nombre de photos restantes sur la carte
- status[35] : Nombre de vidéos restantes sur la carte
- status[61] : Niveau de batterie (%)
- status[30] : Numéro de série
- status[37] : Résolution vidéo (4 = 1080p, autres valeurs à mapper)
- status[39] : Champ de vision (FOV)
- status[57] : Espace utilisé (en Ko ?)
- status[60] : Taille mémoire totale (MB)
- status[64] : Espace libre (MB)

----------------------------------------
⚠️ STATUS (à vérifier)
----------------------------------------
- status[1]  : Mode général (souvent 1=Video, 2=Photo, 3=Timelapse)
- status[4]  : Valeur spéciale (souvent 255 quand non défini)
- status[43–49] : Réglages réseau / streaming (non confirmés)
- status[70–73] : Horloge de la GoPro (heures/minutes/secondes)

----------------------------------------
✅ SETTINGS (confirmés)
----------------------------------------
- settings[17] : Nombre de mégapixels photo
- settings[26] : Résolution vidéo (ex: 4 = 1080p)
- settings[29] : Mode rafale photo
- settings[30] : Intervalle timelapse
- settings[32] : FPS (frames per second)
- settings[84] : Bitrate vidéo (6=High, etc.)

----------------------------------------
⚠️ SETTINGS (à vérifier)
----------------------------------------
- settings[2]  : Orientation (Up/Down/Auto)
- settings[41/42/44/45] : White balance (balance des blancs)
- settings[47] : Netteté (sharpness)
- settings[48] : EV Comp (exposition)
- settings[59] : Hypersmooth (stabilisation électronique)
- settings[80] : Protune On/Off
- settings[81–85] : Paramètres Protune avancés (ISO min/max, etc.)

----------------------------------------
📸 Commandes testées avec succès
----------------------------------------
- gopro.shutter("on")  → démarre enregistrement vidéo
- gopro.shutter("off") → stop enregistrement
- gopro.take_photo()   → prend une photo (en mode photo)
  ⚠️ Nécessite : gopro.mode(constants.Mode.PhotoMode, constants.Mode.SubMode.Photo.Single)

----------------------------------------
🛠 Conseils
----------------------------------------
- Pour explorer : status = gopro.getStatus(constants.Status.Status, id)
                  settings = gopro.getStatus(constants.Status.Settings, id)
- Affiche le JSON brut pour voir tous les IDs disponibles.
- Ajoute toi-même les traductions quand tu confirmes un ID.

Remarque :
On n'utilise PAS gopro.getStatus(...) pour lire tout le JSON (version de la lib trop capricieuse).
On interroge directement http://10.5.5.9/gp/gpControl/status pour la vérité brute.

"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from goprocam import GoProCamera, constants
import requests
import time
import datetime
from pathlib import Path

OUTDIR = Path(__file__).parent / "images"
OUTDIR.mkdir(exist_ok=True)

gopro = GoProCamera.GoPro()

GOPRO_IP = "10.5.5.9"
STATUS_URL = f"http://{GOPRO_IP}/gp/gpControl/status"
MEDIA_URL = f"http://{GOPRO_IP}:8080/videos/DCIM/100GOPRO/"

def wake_gopro():
    """Réveille la GoPro et attend qu'elle soit réellement active."""
    print("⏰ Réveil GoPro...")

    # une requête suffit à la réveiller
    try:
        requests.get(STATUS_URL, timeout=1)
    except:
        pass

    # attendre qu'elle réponde vraiment
    for _ in range(20):  # ~ 4 secondes max
        try:
            r = requests.get(STATUS_URL, timeout=0.5)
            if r.ok and "status" in r.json():
                print("⚡ GoPro réveillée.")
                return True
        except:
            pass
        time.sleep(0.2)
      
    time.sleep(8)

    print("❌ Impossible de réveiller la GoPro.")
    return False


def switch_to_photo_mode():
    print("🎛 Passage en mode Photo / Single...")
    gopro.mode(constants.Mode.PhotoMode, constants.Mode.SubMode.Photo.Single)
    time.sleep(2)


def wait_for_new_media(before_list):
    """Attend qu'un nouveau média arrive dans gpMediaList."""
    for _ in range(25):  # ~5 secondes max
        try:
            listing = gopro.getMediaList()
            last_dir = list(listing["media"].values())[-2]["d"]
            last_file = list(listing["media"].values())[-1]["fs"][-1]["n"]

            file_id = (last_dir, last_file)
            if file_id not in before_list:
                return file_id
        except:
            pass

        time.sleep(0.2)

    return None


def take_photo():
    # 1. Réveil
    if not wake_gopro():
        return

    # 2. Lecture de la liste AVANT la photo
    before = set()
    try:
        listing = gopro.getMediaList()
        d = list(listing["media"].values())[-2]["d"]
        f = list(listing["media"].values())[-1]["fs"][-1]["n"]
        before.add((d, f))
    except:
        pass

    # 3. Mode photo
    switch_to_photo_mode()

    time.sleep(8)

    # 4. Déclenchement
    print("📸 Déclenchement...")
    gopro.shutter(constants.start)

    # 5. Attendre le nouveau fichier
    print("⏳ Attente du fichier...")
    new_media = wait_for_new_media(before)

    if not new_media:
        print("❌ La GoPro n'a pas généré de média.")
        return

    directory, filename = new_media

    # 6. Téléchargement direct dans ton dossier
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    local_path = OUTDIR / f"photo_{ts}.jpg"

    url = f"http://{GOPRO_IP}:8080/videos/DCIM/{directory}/{filename}"

    print("⬇️ Téléchargement :", url)
    r = requests.get(url, stream=True)
    with open(local_path, "wb") as f:
        for chunk in r.iter_content(4096):
            f.write(chunk)

    print(f"✅ Photo sauvegardée : {local_path.resolve()}")


if __name__ == "__main__":
    take_photo()

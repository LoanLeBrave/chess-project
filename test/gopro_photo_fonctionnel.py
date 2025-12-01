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

"""
Script interactif minimal :
- tape "photo" pour prendre une photo et la sauvegarder dans ./images/
- tape "quit" pour quitter

Remarque :
On n'utilise PAS gopro.getStatus(...) pour lire tout le JSON (version de la lib trop capricieuse).
On interroge directement http://10.5.5.9/gp/gpControl/status pour la vérité brute.
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script : prendre une photo et la sauvegarder dans ./images/
⚠️ Assure-toi que la GoPro est déjà en mode PHOTO avant de lancer ce script.
"""

from goprocam import GoProCamera, constants
import os
import time
import datetime
from pathlib import Path

# === CONFIGURATION ===

# Dossier pour sauvegarder les photos
OUTDIR = Path(__file__).parent / "images"
OUTDIR.mkdir(exist_ok=True)

# Connexion GoPro (Wi-Fi en mode gpcontrol)
gopro = GoProCamera.GoPro(constants.gpcontrol)

def switch_to_photo_mode():
    """Met la GoPro en mode Photo / Single."""
    print("🎛 Passage en mode Photo / Single...")
    gopro.mode(constants.Mode.PhotoMode, constants.Mode.SubMode.Photo.Single)
    time.sleep(5.0)  # attendre que le changement de mode soit effectif

def take_photo():
    """Déclenche une photo et télécharge l’image capturée."""
    switch_to_photo_mode()

    print("📸 Déclenchement de la photo...")
    gopro.take_photo()
    time.sleep(7.5)  # attendre que la photo soit bien écrite sur la SD

    # Nom de fichier horodaté
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = OUTDIR / f"photo_{timestamp}.jpg"

    print("⬇️  Téléchargement de la photo...")
    try:
        gopro.downloadLastMedia(custom_filename=str(filename))
        print(f"✅ Photo sauvegardée : {filename.resolve()}")
    except Exception as e:
        print("❌ Échec du téléchargement :", e)

if __name__ == "__main__":
    take_photo()

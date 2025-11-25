# hero7_udp_fix.py
import requests, time, sys, socket, threading
from pathlib import Path

# --- CONFIGURATION ---
IP_GOPRO = "10.5.5.9"
HTTP_BASE = f"http://{IP_GOPRO}"
MEDIA_BASE = f"http://{IP_GOPRO}:8080"
UDP_PORT = 8554
UDP_MESSAGE = b"_GPHD_:0:0:2:0.000000\n" # Le message magique pour Hero 7
OUT_DIR = (Path(__file__).parent / "captures"); OUT_DIR.mkdir(exist_ok=True)

# --- KEEP ALIVE (Vital pour Hero 7) ---
def send_keep_alive():
    """Envoie un paquet UDP toutes les 2.5s pour garder la GoPro réveillée."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        try:
            sock.sendto(UDP_MESSAGE, (IP_GOPRO, UDP_PORT))
            time.sleep(2.5)
        except:
            break

# Lance le keep alive en arrière-plan
ka_thread = threading.Thread(target=send_keep_alive, daemon=True)
ka_thread.start()

# --- FONCTIONS HTTP ---
def get(url, timeout=4, ok=True):
    try:
        r = requests.get(url, timeout=timeout)
        if ok: r.raise_for_status()
        return r
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 500:
            print(f"💥 Erreur 500 (Caméra figée) sur {url}. Fais un reset batterie.")
            sys.exit(1)
        print(f"⚠️ Erreur HTTP: {e}")
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
    return None

def get_status():
    r = get(f"{HTTP_BASE}/gp/gpControl/status")
    if not r: return None
    return r.json().get("status", {})

def check_sd_and_status():
    st = get_status()
    if not st:
        print("❌ Impossible de lire le statut. Vérifie le Wi-Fi.")
        sys.exit(1)

    # Détection SD Robuste (Ignore le flag 31 s'il ment)
    photos_left = st.get("34", -1)
    space_mb    = st.get("64", 0)
    sd_ok       = (space_mb > 0) or (photos_left > 0) or (st.get("31") == 1)
    
    current_mode = st.get("43", -1) # 1 = Photo
    busy_flag    = st.get("8", 0)   # 1 = Occupé

    print(f"🔎 État: Mode={current_mode} | Busy={busy_flag} | SD_OK={sd_ok} (PhotosRestantes={photos_left})")
    
    if not sd_ok:
        print("🚫 ERREUR: Vraiment pas de carte SD (Espace=0, Photos=0).")
        sys.exit(2)
        
    return current_mode, busy_flag

def smart_set_photo_mode(current_mode):
    # Si on est déjà en mode photo (1), on ne fait RIEN pour éviter le crash 500
    if current_mode == 1:
        print("✅ Déjà en mode Photo (pas de changement nécessaire).")
        return

    print("🔄 Passage en mode Photo...")
    get(f"{HTTP_BASE}/gp/gpControl/command/mode?p=1")
    time.sleep(0.5)
    # On force le sub_mode Single (1) juste au cas où
    get(f"{HTTP_BASE}/gp/gpControl/command/sub_mode?mode=1&sub_mode=1")
    time.sleep(0.5)

def shoot_photo():
    print("📸 Tentative de déclenchement...")
    # Parfois un shutter 'off' (p=0) réveille la commande
    try: requests.get(f"{HTTP_BASE}/gp/gpControl/command/shutter?p=0", timeout=1)
    except: pass

    r = get(f"{HTTP_BASE}/gp/gpControl/command/shutter?p=1", ok=False)
    if r and r.status_code == 200:
        print("✅ Commande Shutter reçue.")
        time.sleep(3) # Attente écriture
        return True
    else:
        print(f"❌ Echec Shutter: {r.status_code if r else 'Timeout'}")
        return False

def download_last_media():
    print("📂 Recherche du fichier...")
    try:
        j = get(f"{HTTP_BASE}/gp/gpMediaList").json()
        media_list = j.get("media", [])
        if not media_list: return None
        
        last_dir = media_list[-1]
        if not last_dir.get("fs"): return None
        
        file_info = last_dir["fs"][-1]
        filename = file_info["n"]
        file_path = f"/videos/DCIM/{last_dir['d']}/{filename}"
        
        dl_url = f"{MEDIA_BASE}{file_path}"
        dest_path = OUT_DIR / filename
        
        print(f"⬇️  Téléchargement de {filename}...")
        with requests.get(dl_url, stream=True, timeout=15) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return dest_path
    except Exception as e:
        print(f"⚠️ Erreur téléchargement: {e}")
        return None

def main():
    print("--- Démarrage Hero 7 Controller (avec UDP Keep-Alive) ---")
    
    # 1. Vérifications initiales
    mode, busy = check_sd_and_status()
    
    if busy == 1:
        print("⏳ Caméra occupée, attente 3s...")
        time.sleep(3)

    # 2. Config Mode (Intelligent)
    smart_set_photo_mode(mode)

    # 3. Photo
    if shoot_photo():
        # 4. Téléchargement
        path = download_last_media()
        if path:
            print(f"🎉 Terminé ! Photo sauvée : {path}")
        else:
            print("⚠️ Photo prise, mais fichier introuvable (délai d'écriture ?).")
    else:
        print("❌ La photo n'a pas pu être prise.")

if __name__ == "__main__":
    main()
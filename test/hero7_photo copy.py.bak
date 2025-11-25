# hero7_diag_photo.py
import requests, time, sys, json
from pathlib import Path

HTTP = "http://10.5.5.9"
MEDIA = "http://10.5.5.9:8080"
OUT = (Path(__file__).parent / "captures"); OUT.mkdir(exist_ok=True)

def get(url, to=3, ok=True):
    r = requests.get(url, timeout=to)
    if ok: r.raise_for_status()
    return r

def status():
    r = get(f"{HTTP}/gp/gpControl/status")
    data = r.json()
    # Affiche les principaux voyants si présents
    st = data.get("status", {})
    sd_present  = st.get("31") or st.get(31)  # 0 = pas de SD, 1 = OK (selon modèles)
    sd_err      = st.get("33") or st.get(33)  # 0/1/2 selon état
    busy        = st.get("8")  or st.get(8)   # 0 = prêt, 1 = occupé
    mode        = st.get("43") or st.get(43)  # 0=video,1=photo,2=burst,3=timelapse
    print("🔎 status:", {k: st.get(k) for k in map(str, ("8","31","33","43"))})
    return {"sd_present": sd_present, "sd_err": sd_err, "busy": busy, "mode": mode}

def ready_or_die():
    try:
        get(f"{HTTP}/gp/gpControl/status")
        print("🌐 GoPro OK.")
    except Exception as e:
        print("❌ Pas d’accès à 10.5.5.9. Connecte le Wi-Fi GoPro."); sys.exit(1)

def set_photo_single():
    get(f"{HTTP}/gp/gpControl/command/mode?p=2")                 # Photo
    time.sleep(0.2)
    get(f"{HTTP}/gp/gpControl/command/sub_mode?mode=2&sub_mode=1")  # Single
    print("📷 Photo/Single prêt.")
    time.sleep(0.4)

def shoot():
    # Certains firmwares aiment bien un 'p=0' avant
    try: get(f"{HTTP}/gp/gpControl/command/shutter?p=0", ok=False)
    except: pass
    r = get(f"{HTTP}/gp/gpControl/command/shutter?p=1", ok=False)
    if r.status_code != 200:
        print("❌ Shutter a renvoyé", r.status_code, r.text[:120])
        return False
    print("📸 Déclenché.")
    time.sleep(2.0)
    return True

def last_media_path():
    j = get(f"{HTTP}/gp/gpMediaList").json()
    media = j.get("media", [])
    if not media: return None
    d = media[-1]["d"]; fs = media[-1].get("fs", [])
    if not fs: return None
    return f"/videos/DCIM/{d}/{fs[-1]['n']}"

def download_last():
    rel = last_media_path()
    if not rel:
        print("⚠️ Aucun média listé."); return None
    url = f"{MEDIA}{rel}"
    dest = OUT / Path(rel).name
    print("⬇️", url, "->", dest)
    with requests.get(url, stream=True, timeout=10) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for c in r.iter_content(131072):
                if c: f.write(c)
    return dest

def main():
    ready_or_die()
    s = status()

    if str(s.get("sd_present")) not in ("1", "True"):
        print("🚫 Pas de carte SD détectée → insère/retire le verrou, formate sur la GoPro.")
        sys.exit(2)
    if str(s.get("busy")) == "1":
        print("⏳ Caméra occupée (busy=1). Attends 3s…"); time.sleep(3)

    set_photo_single()
    if not shoot():
        print("➡️ Retente après re-forçage du mode…")
        set_photo_single()
        time.sleep(0.5)
        if not shoot():
            print("❗ Toujours en échec. Vérifie: USB débranché, SD OK, batterie suffisante.")
            sys.exit(3)

    dest = download_last()
    if dest and dest.exists() and dest.stat().st_size > 0:
        print("🎉 OK:", dest.resolve(), f"({dest.stat().st_size} octets)")
    else:
        print("⚠️ Déclenché mais rien listé/téléchargé. Réessaie ou vérifie la SD.")

if __name__ == "__main__":
    main()

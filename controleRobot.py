from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
import sys
import tty
import termios
import json
from datetime import datetime

# Connexion au robot
rtde_c = RTDEControlInterface("192.168.0.11")
rtde_r = RTDEReceiveInterface("192.168.0.11")

# Paramètres de mouvement
STEP_LINEAR = 0.01  # 1 cm
STEP_ANGULAR = 0.05  # ~3 degrés
VELOCITY = 0.25
ACCELERATION = 0.3

# Stockage des positions et séquences
positions_enregistrees = []
sequence_active = []
enregistrement_sequence = False


def get_key():
    """Lit une touche du clavier"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ch == '\x1b':  # Séquence d'échappement (flèches)
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1)
            return ch + ch2 + ch3
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def move_cartesian(dx=0, dy=0, dz=0, drx=0, dry=0, drz=0):
    """Déplace le robot en coordonnées cartésiennes"""
    pose = rtde_r.getActualTCPPose()
    pose[0] += dx
    pose[1] += dy
    pose[2] += dz
    pose[3] += drx
    pose[4] += dry
    pose[5] += drz
    rtde_c.moveL(pose, VELOCITY, ACCELERATION)


def save_position():
    """Enregistre la position actuelle"""
    pose = rtde_r.getActualTCPPose()
    joints = rtde_r.getActualQ()
    position = {
        "tcp": list(pose),
        "joints": list(joints),
        "timestamp": datetime.now().isoformat()
    }
    positions_enregistrees.append(position)
    print(f"\n✓ Position {len(positions_enregistrees)} enregistrée: X={pose[0]:.3f} Y={pose[1]:.3f} Z={pose[2]:.3f}")

    if enregistrement_sequence:
        sequence_active.append(position)
        print(f"  (ajoutée à la séquence, {len(sequence_active)} points)")


def play_sequence():
    """Rejoue la séquence enregistrée"""
    if not sequence_active:
        print("\n⚠ Aucune séquence enregistrée")
        return

    print(f"\n▶ Lecture de la séquence ({len(sequence_active)} positions)...")
    for i, pos in enumerate(sequence_active):
        print(f"  Position {i + 1}/{len(sequence_active)}")
        rtde_c.moveJ(pos["joints"], VELOCITY, ACCELERATION)
    print("✓ Séquence terminée")


def save_to_file():
    """Sauvegarde les positions et séquence dans un fichier"""
    data = {
        "positions": positions_enregistrees,
        "sequence": sequence_active
    }
    filename = f"robot_positions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n✓ Sauvegardé dans {filename}")


def load_from_file(filename):
    """Charge les positions depuis un fichier"""
    global positions_enregistrees, sequence_active
    with open(filename, 'r') as f:
        data = json.load(f)
    positions_enregistrees = data.get("positions", [])
    sequence_active = data.get("sequence", [])
    print(f"\n✓ Chargé: {len(positions_enregistrees)} positions, {len(sequence_active)} points de séquence")


def print_help():
    """Affiche l'aide"""
    print("""
╔════════════════════════════════════════════════════════════╗
║              CONTRÔLE ROBOT UR5 - AIDE                     ║
╠════════════════════════════════════════════════════════════╣
║  DÉPLACEMENT LINÉAIRE:                                     ║
║    ↑/↓     : Avancer/Reculer (Y)                          ║
║    ←/→     : Gauche/Droite (X)                            ║
║    z/s     : Monter/Descendre (Z)                         ║
║                                                            ║
║  ROTATION:                                                 ║
║    a/e     : Rotation X (rx)                              ║
║    q/d     : Rotation Y (ry)                              ║
║    w/x     : Rotation Z (rz)                              ║
║                                                            ║
║  ENREGISTREMENT:                                           ║
║    ESPACE  : Enregistrer position actuelle                ║
║    r       : Démarrer/Arrêter enregistrement séquence     ║
║    p       : Rejouer la séquence                          ║
║    l       : Sauvegarder dans fichier                     ║
║                                                            ║
║  AUTRES:                                                   ║
║    i       : Afficher position actuelle                   ║
║    h       : Afficher cette aide                          ║
║    ECHAP   : Quitter                                       ║
╚════════════════════════════════════════════════════════════╝
""")


def main():
    global enregistrement_sequence

    print("Connexion au robot...")
    print(f"Position TCP actuelle: {rtde_r.getActualTCPPose()}")
    print_help()

    while True:
        key = get_key()

        # Flèches directionnelles
        if key == '\x1b[A':  # Flèche haut
            print("↑ Y+")
            move_cartesian(dy=STEP_LINEAR)
        elif key == '\x1b[B':  # Flèche bas
            print("↓ Y-")
            move_cartesian(dy=-STEP_LINEAR)
        elif key == '\x1b[C':  # Flèche droite
            print("→ X+")
            move_cartesian(dx=STEP_LINEAR)
        elif key == '\x1b[D':  # Flèche gauche
            print("← X-")
            move_cartesian(dx=-STEP_LINEAR)

        # Hauteur Z
        elif key == 'z':
            print("Z+ (monter)")
            move_cartesian(dz=STEP_LINEAR)
        elif key == 's':
            print("Z- (descendre)")
            move_cartesian(dz=-STEP_LINEAR)

        # Rotations
        elif key == 'a':
            print("RX+")
            move_cartesian(drx=STEP_ANGULAR)
        elif key == 'e':
            print("RX-")
            move_cartesian(drx=-STEP_ANGULAR)
        elif key == 'q':
            print("RY+")
            move_cartesian(dry=STEP_ANGULAR)
        elif key == 'd':
            print("RY-")
            move_cartesian(dry=-STEP_ANGULAR)
        elif key == 'w':
            print("RZ+")
            move_cartesian(drz=STEP_ANGULAR)
        elif key == 'x':
            print("RZ-")
            move_cartesian(drz=-STEP_ANGULAR)

        # Enregistrement
        elif key == ' ':
            save_position()
        elif key == 'r':
            enregistrement_sequence = not enregistrement_sequence
            if enregistrement_sequence:
                sequence_active.clear()
                print("\n● ENREGISTREMENT SÉQUENCE DÉMARRÉ")
            else:
                print(f"\n■ ENREGISTREMENT ARRÊTÉ ({len(sequence_active)} positions)")
        elif key == 'p':
            play_sequence()
        elif key == 'l':
            save_to_file()

        # Infos
        elif key == 'i':
            pose = rtde_r.getActualTCPPose()
            joints = rtde_r.getActualQ()
            print(f"\nPosition TCP: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}")
            print(f"Orientation:  RX={pose[3]:.4f} RY={pose[4]:.4f} RZ={pose[5]:.4f}")
            print(f"Joints (rad): {[f'{j:.3f}' for j in joints]}")
        elif key == 'h':
            print_help()

        # Quitter
        elif key == '\x1b' or key == '\x03':  # ESC ou Ctrl+C
            print("\nArrêt du programme...")
            break

    rtde_c.stopScript()
    print("Déconnecté")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nErreur: {e}")
        rtde_c.stopScript()
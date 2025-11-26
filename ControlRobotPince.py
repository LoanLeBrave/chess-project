from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from robotiq_gripper_control import RobotiqGripper
import sys
import tty
import termios
import json
from datetime import datetime
import time

# Connexions
rtde_c = RTDEControlInterface("192.168.0.11")
rtde_r = RTDEReceiveInterface("192.168.0.11")

# Initialisation du gripper
gripper = RobotiqGripper(rtde_c)
print("Activation du gripper...")
gripper.activate()
gripper.set_force(50)
gripper.set_speed(100)
print("Gripper prêt !")

# Paramètres
STEP_LINEAR = 0.01
STEP_ANGULAR = 0.05
VELOCITY = 0.25
ACCELERATION = 0.3

gripper_ouvert = True
positions_enregistrees = []
sequence_active = []
enregistrement_sequence = False


def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1)
            return ch + ch2 + ch3
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def gripper_open():
    global gripper_ouvert
    gripper.open()
    gripper_ouvert = True
    print("✋ Gripper OUVERT")


def gripper_close():
    global gripper_ouvert
    gripper.close()
    gripper_ouvert = False
    print("✊ Gripper FERMÉ")


def gripper_toggle():
    if gripper_ouvert:
        gripper_close()
    else:
        gripper_open()


def gripper_position(pos_mm):
    gripper.move(pos_mm)
    print(f"🤏 Gripper position: {pos_mm}mm")


def move_cartesian(dx=0, dy=0, dz=0, drx=0, dry=0, drz=0):
    pose = rtde_r.getActualTCPPose()
    pose[0] += dx
    pose[1] += dy
    pose[2] += dz
    pose[3] += drx
    pose[4] += dry
    pose[5] += drz
    rtde_c.moveL(pose, VELOCITY, ACCELERATION)


def save_position():
    pose = rtde_r.getActualTCPPose()
    joints = rtde_r.getActualQ()
    position = {
        "tcp": list(pose),
        "joints": list(joints),
        "gripper": "ouvert" if gripper_ouvert else "ferme",
        "timestamp": datetime.now().isoformat()
    }
    positions_enregistrees.append(position)
    print(
        f"\n✓ Position {len(positions_enregistrees)}: X={pose[0]:.3f} Y={pose[1]:.3f} Z={pose[2]:.3f} | Gripper: {position['gripper']}")

    if enregistrement_sequence:
        sequence_active.append(position)
        print(f"  (séquence: {len(sequence_active)} points)")


def play_sequence():
    if not sequence_active:
        print("\n⚠ Aucune séquence")
        return

    print(f"\n▶ Lecture ({len(sequence_active)} positions)...")
    for i, pos in enumerate(sequence_active):
        print(f"  {i + 1}/{len(sequence_active)}")
        rtde_c.moveJ(pos["joints"], VELOCITY, ACCELERATION)

        if pos.get("gripper") == "ouvert":
            gripper_open()
        else:
            gripper_close()
        time.sleep(0.3)

    print("✓ Terminé")


def save_to_file():
    data = {"positions": positions_enregistrees, "sequence": sequence_active}
    filename = f"robot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n✓ Sauvegardé: {filename}")


def load_from_file(filename):
    global positions_enregistrees, sequence_active
    with open(filename, 'r') as f:
        data = json.load(f)
    positions_enregistrees = data.get("positions", [])
    sequence_active = data.get("sequence", [])
    print(f"\n✓ Chargé: {len(positions_enregistrees)} positions, {len(sequence_active)} points")


def print_help():
    print("""
╔═══════════════════════════════════════════════════════════╗
║              CONTRÔLE ROBOT UR5e + Hand-E                 ║
╠═══════════════════════════════════════════════════════════╣
║  DÉPLACEMENT:                                             ║
║    ↑/↓     : Avancer/Reculer (Y)                         ║
║    ←/→     : Gauche/Droite (X)                           ║
║    z/s     : Monter/Descendre (Z)                        ║
║    a/e     : Rotation RX                                 ║
║    q/d     : Rotation RY                                 ║
║    w/x     : Rotation RZ                                 ║
║                                                           ║
║  GRIPPER:                                                 ║
║    g       : Ouvrir/Fermer (toggle)                      ║
║    o       : Ouvrir                                      ║
║    c       : Fermer                                      ║
║    1-9     : Position (1=0mm ouvert, 9=50mm fermé)       ║
║                                                           ║
║  ENREGISTREMENT:                                          ║
║    ESPACE  : Enregistrer position actuelle               ║
║    r       : Démarrer/Arrêter enregistrement séquence    ║
║    p       : Rejouer la séquence                         ║
║    l       : Sauvegarder dans fichier                    ║
║                                                           ║
║  AUTRES:                                                  ║
║    i       : Afficher position actuelle                  ║
║    h       : Afficher cette aide                         ║
║    ECHAP   : Quitter                                     ║
╚═══════════════════════════════════════════════════════════╝
""")


def main():
    global enregistrement_sequence

    print("Connexion au robot...")
    print(f"TCP: {rtde_r.getActualTCPPose()}")
    print_help()

    while True:
        key = get_key()

        # Flèches directionnelles
        if key == '\x1b[A':
            print("↑ Y+")
            move_cartesian(dy=STEP_LINEAR)
        elif key == '\x1b[B':
            print("↓ Y-")
            move_cartesian(dy=-STEP_LINEAR)
        elif key == '\x1b[C':
            print("→ X+")
            move_cartesian(dx=STEP_LINEAR)
        elif key == '\x1b[D':
            print("← X-")
            move_cartesian(dx=-STEP_LINEAR)

        # Hauteur Z
        elif key == 'z':
            print("Z+")
            move_cartesian(dz=STEP_LINEAR)
        elif key == 's':
            print("Z-")
            move_cartesian(dz=-STEP_LINEAR)

        # Rotations
        elif key == 'a':
            move_cartesian(drx=STEP_ANGULAR)
        elif key == 'e':
            move_cartesian(drx=-STEP_ANGULAR)
        elif key == 'q':
            move_cartesian(dry=STEP_ANGULAR)
        elif key == 'd':
            move_cartesian(dry=-STEP_ANGULAR)
        elif key == 'w':
            move_cartesian(drz=STEP_ANGULAR)
        elif key == 'x':
            move_cartesian(drz=-STEP_ANGULAR)

        # Gripper
        elif key == 'g':
            gripper_toggle()
        elif key == 'o':
            gripper_open()
        elif key == 'c':
            gripper_close()
        elif key in '123456789':
            # 1 = 0mm (ouvert), 9 = 50mm (fermé pour Hand-E)
            pos_mm = int((int(key) - 1) * 50 / 8)
            gripper_position(pos_mm)

        # Enregistrement
        elif key == ' ':
            save_position()
        elif key == 'r':
            enregistrement_sequence = not enregistrement_sequence
            if enregistrement_sequence:
                sequence_active.clear()
                print("\n● ENREGISTREMENT DÉMARRÉ")
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
            print(f"Gripper: {'OUVERT' if gripper_ouvert else 'FERMÉ'}")
        elif key == 'h':
            print_help()

        # Quitter
        elif key == '\x1b' or key == '\x03':
            print("\nArrêt...")
            break

    rtde_c.stopScript()
    print("Déconnecté")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nErreur: {e}")
        rtde_c.stopScript()
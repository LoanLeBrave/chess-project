from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from robotiq_gripper import RobotiqGripper
import sys
import tty
import termios
import json
from datetime import datetime
import time

# Connexions
rtde_c = RTDEControlInterface("192.168.0.11")
rtde_r = RTDEReceiveInterface("192.168.0.11")

# Connexion au gripper Robotiq
gripper = RobotiqGripper()
gripper.connect("192.168.0.11", 63352)  # Port par défaut du gripper
gripper.activate()

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
    gripper.move(0, 255, 255)  # Position 0 = ouvert, vitesse max, force max
    gripper_ouvert = True
    print("✋ Gripper OUVERT")


def gripper_close():
    global gripper_ouvert
    gripper.move(255, 255, 255)  # Position 255 = fermé
    gripper_ouvert = False
    print("✊ Gripper FERMÉ")


def gripper_toggle():
    if gripper_ouvert:
        gripper_close()
    else:
        gripper_open()


def gripper_position(pos):
    gripper.move(pos, 255, 255)
    print(f"🤏 Gripper position: {pos}")


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
        time.sleep(0.5)

    print("✓ Terminé")


def save_to_file():
    data = {"positions": positions_enregistrees, "sequence": sequence_active}
    filename = f"robot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n✓ Sauvegardé: {filename}")


def print_help():
    print("""
╔═══════════════════════════════════════════════════════════╗
║              CONTRÔLE ROBOT UR5                           ║
╠═══════════════════════════════════════════════════════════╣
║  ↑↓←→ : Déplacement X/Y    z/s : Haut/Bas (Z)            ║
║  a/e q/d w/x : Rotations RX/RY/RZ                        ║
║  g : Toggle gripper   o : Ouvrir   c : Fermer            ║
║  1-9 : Position gripper (1=ouvert, 9=fermé)              ║
║  ESPACE : Enregistrer   r : Séquence on/off              ║
║  p : Rejouer   l : Sauvegarder   i : Info   h : Aide     ║
║  ECHAP : Quitter                                          ║
╚═══════════════════════════════════════════════════════════╝
""")


def main():
    global enregistrement_sequence

    print("Connexion...")
    print(f"TCP: {rtde_r.getActualTCPPose()}")
    print_help()

    while True:
        key = get_key()

        if key == '\x1b[A':
            move_cartesian(dy=STEP_LINEAR)
        elif key == '\x1b[B':
            move_cartesian(dy=-STEP_LINEAR)
        elif key == '\x1b[C':
            move_cartesian(dx=STEP_LINEAR)
        elif key == '\x1b[D':
            move_cartesian(dx=-STEP_LINEAR)
        elif key == 'z':
            move_cartesian(dz=STEP_LINEAR)
        elif key == 's':
            move_cartesian(dz=-STEP_LINEAR)
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
        elif key == 'g':
            gripper_toggle()
        elif key == 'o':
            gripper_open()
        elif key == 'c':
            gripper_close()
        elif key in '123456789':
            pos = int((int(key) - 1) * 255 / 8)
            gripper_position(pos)
        elif key == ' ':
            save_position()
        elif key == 'r':
            enregistrement_sequence = not enregistrement_sequence
            if enregistrement_sequence:
                sequence_active.clear()
                print("\n● REC ON")
            else:
                print(f"\n■ REC OFF ({len(sequence_active)} pts)")
        elif key == 'p':
            play_sequence()
        elif key == 'l':
            save_to_file()
        elif key == 'i':
            pose = rtde_r.getActualTCPPose()
            print(f"\nTCP: {pose[0]:.4f}, {pose[1]:.4f}, {pose[2]:.4f}")
        elif key == 'h':
            print_help()
        elif key == '\x1b' or key == '\x03':
            break

    gripper.disconnect()
    rtde_c.stopScript()
    print("Déconnecté")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erreur: {e}")
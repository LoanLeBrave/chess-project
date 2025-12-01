from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from robotiq_gripper_control import RobotiqGripper
import sys
import tty
import termios
import json
from datetime import datetime
import time
import select

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
SPEED = 0.1  # m/s pour les mouvements linéaires
SPEED_ROT = 0.3  # rad/s pour les rotations
ACCELERATION = 0.5

gripper_ouvert = True
positions_enregistrees = []
sequence_active = []
enregistrement_sequence = False


def get_key_non_blocking():
    """Lit une touche sans bloquer"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
        if rlist:
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                ch2 = sys.stdin.read(1)
                ch3 = sys.stdin.read(1)
                return ch + ch2 + ch3
            return ch
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def move_speed(vx=0, vy=0, vz=0, vrx=0, vry=0, vrz=0):
    """Déplace le robot avec une vitesse donnée"""
    rtde_c.speedL([vx, vy, vz, vrx, vry, vrz], ACCELERATION, 0.1)


def stop_robot():
    """Arrête le mouvement du robot"""
    rtde_c.speedStop()


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
        rtde_c.moveJ(pos["joints"], 0.5, 0.3)

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


def print_help():
    print("""
╔═══════════════════════════════════════════════════════════╗
║         CONTRÔLE ROBOT UR5e + Hand-E (Mode Fluide)        ║
╠═══════════════════════════════════════════════════════════╣
║  DÉPLACEMENT (maintenir la touche):                       ║
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
║    1-9     : Position (1=ouvert, 9=fermé)                ║
║                                                           ║
║  ENREGISTREMENT:                                          ║
║    ESPACE  : Enregistrer position actuelle               ║
║    r       : Démarrer/Arrêter enregistrement séquence    ║
║    p       : Rejouer la séquence                         ║
║    l       : Sauvegarder dans fichier                    ║
║                                                           ║
║  VITESSE:                                                 ║
║    +/-     : Augmenter/Diminuer la vitesse               ║
║                                                           ║
║  AUTRES:                                                  ║
║    i       : Afficher position actuelle                  ║
║    h       : Afficher cette aide                         ║
║    ECHAP   : Quitter                                     ║
╚═══════════════════════════════════════════════════════════╝
""")


def main():
    global enregistrement_sequence, SPEED, SPEED_ROT

    print("Connexion au robot...")
    print(f"TCP: {rtde_r.getActualTCPPose()}")
    print_help()

    current_velocity = [0, 0, 0, 0, 0, 0]
    last_key = None

    while True:
        key = get_key_non_blocking()

        # Reset velocity si aucune touche
        new_velocity = [0, 0, 0, 0, 0, 0]

        if key:
            # Flèches directionnelles
            if key == '\x1b[A':
                new_velocity[1] = SPEED  # Y+
            elif key == '\x1b[B':
                new_velocity[1] = -SPEED  # Y-
            elif key == '\x1b[C':
                new_velocity[0] = SPEED  # X+
            elif key == '\x1b[D':
                new_velocity[0] = -SPEED  # X-

            # Hauteur Z
            elif key == 'z':
                new_velocity[2] = SPEED  # Z+
            elif key == 's':
                new_velocity[2] = -SPEED  # Z-

            # Rotations
            elif key == 'a':
                new_velocity[3] = SPEED_ROT
            elif key == 'e':
                new_velocity[3] = -SPEED_ROT
            elif key == 'q':
                new_velocity[4] = SPEED_ROT
            elif key == 'd':
                new_velocity[4] = -SPEED_ROT
            elif key == 'w':
                new_velocity[5] = SPEED_ROT
            elif key == 'x':
                new_velocity[5] = -SPEED_ROT

            # Gripper
            elif key == 'g':
                stop_robot()
                gripper_toggle()
            elif key == 'o':
                stop_robot()
                gripper_open()
            elif key == 'c':
                stop_robot()
                gripper_close()
            elif key in '123456789':
                stop_robot()
                pos_mm = int((int(key) - 1) * 50 / 8)
                gripper_position(pos_mm)

            # Enregistrement
            elif key == ' ':
                stop_robot()
                save_position()
            elif key == 'r':
                stop_robot()
                enregistrement_sequence = not enregistrement_sequence
                if enregistrement_sequence:
                    sequence_active.clear()
                    print("\n● ENREGISTREMENT DÉMARRÉ")
                else:
                    print(f"\n■ ENREGISTREMENT ARRÊTÉ ({len(sequence_active)} positions)")
            elif key == 'p':
                stop_robot()
                play_sequence()
            elif key == 'l':
                stop_robot()
                save_to_file()

            # Vitesse
            elif key == '+':
                SPEED = min(SPEED + 0.02, 0.5)
                SPEED_ROT = min(SPEED_ROT + 0.1, 1.0)
                print(f"Vitesse: {SPEED:.2f} m/s | {SPEED_ROT:.2f} rad/s")
            elif key == '-':
                SPEED = max(SPEED - 0.02, 0.02)
                SPEED_ROT = max(SPEED_ROT - 0.1, 0.1)
                print(f"Vitesse: {SPEED:.2f} m/s | {SPEED_ROT:.2f} rad/s")

            # Infos
            elif key == 'i':
                stop_robot()
                pose = rtde_r.getActualTCPPose()
                print(f"\nTCP: X={pose[0]:.4f} Y={pose[1]:.4f} Z={pose[2]:.4f}")
                print(f"Rot: RX={pose[3]:.4f} RY={pose[4]:.4f} RZ={pose[5]:.4f}")
                print(f"Vitesse: {SPEED:.2f} m/s | Gripper: {'OUVERT' if gripper_ouvert else 'FERMÉ'}")
            elif key == 'h':
                stop_robot()
                print_help()

            # Quitter
            elif key == '\x1b' or key == '\x03':
                print("\nArrêt...")
                break

        # Appliquer la vitesse si mouvement demandé
        if any(v != 0 for v in new_velocity):
            rtde_c.speedL(new_velocity, ACCELERATION, 0.1)
        elif any(v != 0 for v in current_velocity):
            # Arrêter si on relâche la touche
            stop_robot()

        current_velocity = new_velocity

    stop_robot()
    rtde_c.stopScript()
    print("Déconnecté")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nErreur: {e}")
        rtde_c.speedStop()
        rtde_c.stopScript()
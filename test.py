from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface

import time

rtde_c = RTDEControlInterface("192.168.0.11")
rtde_r = RTDEReceiveInterface("192.168.0.11")

print("Connexion OK")

# Lire la position actuelle
position_actuelle = rtde_r.getActualQ()
print("Position actuelle (rad):", position_actuelle)

# Petit mouvement sur le premier axe (+0.1 rad ≈ 5.7°)
nouvelle_position = list(position_actuelle)
nouvelle_position[0] += 0.1

print("Déplacement vers:", nouvelle_position)
rtde_c.moveJ(nouvelle_position, 0.5, 0.3)  # vitesse=0.5 rad/s, accélération=0.3 rad/s²

print("Mouvement terminé")
print("Nouvelle position:", rtde_r.getActualQ())

rtde_c.stopScript()
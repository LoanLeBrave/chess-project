from rtde_control import RTDEControlInterface
import time

rtde_c = RTDEControlInterface("192.168.0.11")

# Script complet pour activer et fermer le gripper
script_close = """
rq_activate_and_wait()
rq_set_force(100)
rq_set_speed(100)
rq_close_and_wait()
"""

script_open = """
rq_open_and_wait()
"""

print("Activation et fermeture...")
rtde_c.sendCustomScriptFunction("close_gripper", script_close)
time.sleep(3)

print("Ouverture...")
rtde_c.sendCustomScriptFunction("open_gripper", script_open)
time.sleep(2)

rtde_c.stopScript()
print("Terminé")
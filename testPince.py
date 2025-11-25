from rtde_control import RTDEControlInterface
import time

rtde_c = RTDEControlInterface("192.168.0.11")

# Test fermeture du gripper
print("Test fermeture...")
rtde_c.sendCustomScriptFunction("gripper_close", "rq_close()")
time.sleep(2)

# Test ouverture
print("Test ouverture...")
rtde_c.sendCustomScriptFunction("gripper_open", "rq_open()")
time.sleep(2)

rtde_c.stopScript()
print("Terminé")
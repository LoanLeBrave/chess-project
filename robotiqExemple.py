from robotiq_gripper_control import RobotiqGripper
from rtde_control import RTDEControlInterface
import time

rtde_c = RTDEControlInterface("192.168.0.11")
gripper = RobotiqGripper(rtde_c)

# Activate the gripper and initialize force and speed
gripper.activate()  # returns to previous position after activation
gripper.set_force(50)  # from 0 to 100 %
gripper.set_speed(100)  # from 0 to 100 %

# Perform some gripper actions
gripper.open()
gripper.close()
time.sleep(1)
gripper.open()
gripper.move(55)  # mm

print("Finish")

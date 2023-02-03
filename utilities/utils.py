# !/usr/bin/env python3

import time
import sys

from RpiMotorLib import RpiMotorLib


def updateGauge(gpio, steps):
    """main function loop"""

    direction = False
    if steps >= 0:
        direction = True

    # Declare a named instance of class pass a name and type of motor
    mymotortest = RpiMotorLib.BYJMotor("MyMotorOne", "28BYJ")

    time.sleep(1)
    mymotortest.motor_run(gpio, .01, steps, direction, False, "wave", .05)

    # GPIO.cleanup()
    sys.exit()


# =====================END===============================


def calculate_gauge(current_value, previous_value, max_degree, min_value, max_value, max_steps):
    degree_step = max_degree / max_value
    value_step = max_steps / max_value
    if abs(current_value) > abs(max_value):
        if current_value < 0:
            current_value = -max_value
        else:
            current_value = max_value
    if current_value < 0 & min_value >= 0:
        current_value = 0
    current_degree = degree_step * current_value
    current_step = value_step * current_value
    value_to_move = -(previous_value - current_value)
    degree_to_move = degree_step * value_to_move
    steps_to_move = value_step * value_to_move
    previous_degree = current_degree - degree_to_move
    percentage = current_value / max_value * 100
    return current_value, current_degree, degree_to_move, value_to_move, previous_degree, steps_to_move, percentage, \
           current_step

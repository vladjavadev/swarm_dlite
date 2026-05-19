import Adafruit_BBIO.PWM as PWM
import Adafruit_BBIO.GPIO as GPIO
import sys
import time

print("Python-Interpreter: {}\n".format(sys.version))

# Beide Motoren werden mit unterschiedlichen PWM angesteuert
pin_FmotL = "P9_14" # GPIO 50 PWMA linker Motor
pin_FmotR = "P9_21" # GPIO 51 PWMB rechter Motor

pin_BmotL = "P9_16" # GPIO 50 PWMA linker Motor
pin_BmotR = "P9_22" # GPIO 51 PWMB rechter Motor
# Eingänge In2 und In2 invertiert zueinander (geben Drehrichtung vor)

# PWM Parameter
FREQ = 250000
duty_levels = [30, 45, 60, 75, 90]
vModeMin = 0
vModeMax = 4

def get_dc(vMode):
    if vMode>vModeMin and vMode<=vModeMax:
        dc = duty_levels[vMode]
        return dc
    else:
        return duty_levels[0]

def init():
    PWM.start(pin_FmotL, 0, FREQ, 0)
    PWM.start(pin_FmotR, 0, FREQ, 0)
    PWM.start(pin_BmotL, 0, FREQ, 0)
    PWM.start(pin_BmotR, 0, FREQ, 0)


def turnLeft(dTime, vMode=1):
    dc = get_dc(vMode)
    PWM.set_duty_cycle(pin_FmotL, dc)
    PWM.set_duty_cycle(pin_FmotR, 0)
    time.sleep(dTime)

def turnRight(dTime, vMode=1):
    dc = get_dc(vMode)
    PWM.set_duty_cycle(pin_FmotR, dc)
    PWM.set_duty_cycle(pin_FmotL, 0)
    time.sleep(dTime)

def stop():
    PWM.set_duty_cycle(pin_FmotL, 0)
    PWM.set_duty_cycle(pin_FmotR, 0)
    PWM.set_duty_cycle(pin_BmotL, 0)
    PWM.set_duty_cycle(pin_BmotR, 0)
    time.sleep(0.3)


def forward(vMode=1):
    dc = get_dc(vMode)
    PWM.set_duty_cycle(pin_FmotL, dc)
    PWM.set_duty_cycle(pin_FmotR, dc)


def reverse(vMode=1):
    dc = get_dc(vMode)
    PWM.set_duty_cycle(pin_BmotL, dc)
    PWM.set_duty_cycle(pin_BmotR, dc)


# 
# MegaMosquito's Servo Tester
#
# Code for my Raspberry Pi Pico Servo Tester.
#

from machine import Pin, PWM, I2C
from ssd1306 import SSD1306_I2C
from time import sleep_ms

# Basic switchable debugging
DEBUG = False
def debug(str):
  if DEBUG:
    print(str)
    
# OLED display config
OLED_WIDTH  = 128
OLED_HEIGHT = 64
i2c = I2C(0)
oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)

# Servo config
PIN_SERVO = 28
servo = Pin(PIN_SERVO)
pwm_servo = PWM(servo)
FREQUENCY_MIN = 10
FREQUENCY_MAX = 200
SERVO_MIN_MIN = 0
SERVO_MIN_MAX = 5000
SERVO_MAX_MIN = 5001
SERVO_MAX_MAX = 10000

# Initial values for the globals
g_frequency = 50
g_servo_min = 2500
g_servo_max = 8750
g_powered = False
g_percent = 50

# Buttons, with one wire connected to ground (so they need a pullup)
PIN_BUTTON_YELLOW = 26
PIN_BUTTON_BLUE = 27
button_yellow = Pin(PIN_BUTTON_YELLOW, Pin.IN, Pin.PULL_UP)
button_blue = Pin(PIN_BUTTON_BLUE, Pin.IN, Pin.PULL_UP)

# LEDS and relay
PIN_LED_RGB_GREEN = 18
PIN_LED_RGB_BLUE = 19
PIN_LED_POWER = 21
PIN_RELAY = 16
PIN_LED_ONBOARD = 25
led_onboard = Pin(PIN_LED_ONBOARD, Pin.OUT)
led_rgb_green = Pin(PIN_LED_RGB_GREEN, Pin.OUT)
pwm_green = PWM(led_rgb_green)
led_rgb_blue = Pin(PIN_LED_RGB_BLUE, Pin.OUT)
pwm_blue = PWM(led_rgb_blue)
led_power = Pin(PIN_LED_POWER, Pin.OUT)
pwm_power = PWM(led_power)
relay = Pin(PIN_RELAY, Pin.OUT)
pwm_green.freq(1000)
pwm_blue.freq(1000)
pwm_power.freq(1000)
PWM_ON = 2000
PWM_OFF = 0

# Setup the rotary encoder
PIN_ROTARY_CLK = 3
PIN_ROTARY_DT = 2
from rotary_irq_pico import RotaryIRQ
r = RotaryIRQ(pin_num_clk=PIN_ROTARY_CLK, 
              pin_num_dt=PIN_ROTARY_DT, 
              min_val=0, 
              max_val=100, 
              reverse=False, 
              range_mode=RotaryIRQ.RANGE_UNBOUNDED,
              pull_up=True)

# Clamp a value within a range, inclusive of endpoints
def clamp(val, val_min, val_max):
  return max(val_min, min(val, val_max))

# Check to see if the passed button is pressed. If not, return False.
# If so, wait until it is released, then return True.
def button_pressed(b):
  if b.value() == 0:
    while b.value() == 0:
      sleep_ms(50)
    return True
  return False

# Screen management for the "run_test" function
def show_test_details():
  powered_str = "NO"
  if g_powered: powered_str = "YES"
  percent_str = str(g_percent) + "%"
  debug("show_test_details(\"" + powered_str + "\", \"" + percent_str + "\")")
  oled.fill(0)
  oled.text("MegaMosquito's",5,5)
  oled.text("Servo Tester",5,15)
  oled.text("* powered=" + powered_str,5,40)
  oled.text("* percent=" + percent_str,5,50)
  oled.show()

# Manipulate the servo
def update_servo():
  debug("update_servo(\"" + str(g_percent) + "%\")")
  fraction = g_percent / 100.0
  duty = int(g_servo_min + fraction * (g_servo_max - g_servo_min))
  debug("--> duty == " + str(duty))
  pwm_servo.duty_u16(duty)

# Run a servo test (rotary encoder sets duty cycle, and blue button controls power.
def run_test():
  # Set the PWM frequency for the servo
  pwm_servo.freq(g_frequency)
  # Force the initial setting to 50%
  global g_percent
  g_percent = 50
  # Disconnect the servo initially
  global g_powered
  g_powered = False
  relay.value(1)
  # Set the RGB LED (blue means servo off, green means powered on)
  pwm_blue.duty_u16(PWM_ON)
  pwm_green.duty_u16(PWM_OFF)
  # Show the initial settings on the display
  show_test_details()
  update_servo()
  # Loop (until yellow button is pressed) reading rotary encoder and buttons
  # and controlling the servo power relay relay and the servo duty setting.
  r_val_old = r.value()
  keep_going = True
  while keep_going:
    sleep_ms(50)
    # Yellow button is the "go back" button.
    if button_pressed(button_yellow):
      debug("BUTTON_YELLOW (\"go back\")")
      pwm_green.duty_u16(PWM_OFF)
      keep_going = False
    # Blue button controls whether or not the servo is powered (i.e., relay is on)
    if button_pressed(button_blue):
      debug("BUTTON_BLUE (\"toggle power relay\")")
      g_powered = not g_powered
      if g_powered:
        pwm_blue.duty_u16(PWM_OFF)
        pwm_green.duty_u16(PWM_ON)
        relay.value(0)
      else:
        pwm_blue.duty_u16(PWM_ON)
        pwm_green.duty_u16(PWM_OFF)
        relay.value(1)
      debug("--> powered=" + str(g_powered))
      # Update the display 
      show_test_details()
      # Make sure the servo is updated accordingly
      update_servo()
    # Manage the rotary encoder (rotate the servo)
    r_val_new = r.value()
    if r_val_old != r_val_new:
      # Value has changed...
      diff = r_val_old - r_val_new
      #debug("--> diff == " + str(int(diff)))
      r_val_old = r_val_new
      g_percent += diff
      if g_percent < 0: g_percent = 0
      if g_percent > 100: g_percent = 100
      # Update the display
      show_test_details()
      # Manipulate the servo accordingly (ignored if powered off)
      update_servo()
  pwm_blue.duty_u16(PWM_OFF)
  pwm_green.duty_u16(PWM_OFF)
  g_powered = False
  relay.value(1)

# Screen output when adjusting one of the adjustable settings
def show_one_setting(setting_name, setting_min, setting_max, value):
  oled.fill(0)
  oled.text("MegaMosquito's",5,5)
  oled.text("Set: " + setting_name,5,15)
  oled.text("{" + str(setting_min) + "..." + str(setting_max) + "}",5,25)
  oled.text("--> " + str(value),5,40)
  oled.text("YB:Cancel,BB:OK",5,50)
  oled.show()

# Manage the update (or cancellation) of a single adjustable setting
def update_one_setting(setting_name, setting_min, setting_max, original_value):
  r_val_old = r.value()
  value = original_value
  show_one_setting(setting_name, setting_min, setting_max, value)
  while True:
    # Yellow button is the "cancel" button.
    if button_pressed(button_yellow):
      debug("BUTTON_YELLOW (\"cancel\")")
      return original_value
    # Blue button is the "okay" button.
    if button_pressed(button_blue):
      debug("BUTTON_BLUE (\"okay\")")
      return value
    # Manage the rotary encoder (adjust this one setting value)
    r_val_new = r.value()
    if r_val_old != r_val_new:
      diff = r_val_old - r_val_new
      #debug("--> diff == " + str(int(diff)))
      r_val_old = r_val_new
      value = clamp(value + diff, setting_min, setting_max)
      show_one_setting(setting_name, setting_min, setting_max, value)

# Adjust the servo frequency value
def set_frequency():
  debug("set_fequency()")
  global g_frequency
  g_frequency = update_one_setting("frequency", FREQUENCY_MIN, FREQUENCY_MAX, g_frequency)

# Adjust the servo min value
def set_min():
  debug("set_min()")
  global g_servo_min
  g_servo_min = update_one_setting("servo min", SERVO_MIN_MIN, SERVO_MIN_MAX, g_servo_min)

# Adjust the servo max value
def set_max():
  debug("set_max()")
  global g_servo_max
  g_servo_max = update_one_setting("servo max", SERVO_MAX_MIN, SERVO_MAX_MAX, g_servo_max)

# Screen management for the settings menu
def show_settings_menu(which):
  str_freq = "    "
  str_min = "    "
  str_max = "    "
  if which == 0: str_freq = " ==>"
  if which == 1: str_min = " ==>"
  if which == 2: str_max = " ==>"
  oled.fill(0)
  oled.text("MegaMosquito's",5,5)
  oled.text("Settings:",5,15)
  oled.text(str_freq + " Freq(" + str(g_frequency) + ")",5,30)
  oled.text(str_min + " Min(" + str(g_servo_min) + ")",5,40)
  oled.text(str_max + " Max(" + str(g_servo_max) + ")",5,50)
  oled.show()

# Select which setting to adjust
def settings():
  # Loop (until yellow button is pressed) managing settings
  keep_going = True
  r_val_old = r.value()
  which = 0
  show_settings_menu(which)
  while keep_going:
    sleep_ms(50)
    # Yellow button is the "go back" button.
    if button_pressed(button_yellow):
      debug("BUTTON_YELLOW (\"go back\")")
      keep_going = False
    # Blue button is the "select" button.
    if button_pressed(button_blue):
      debug("BUTTON_BLUE (\"select\")")
      if which == 0:
        set_frequency()
      elif which == 1:
        set_min()
      else:
        set_max()
      show_settings_menu(which)
    # Manage the rotary encoder and select a setting to adjust
    r_val_new = r.value()
    if r_val_old != r_val_new:
      diff = r_val_old - r_val_new
      #debug("--> diff == " + str(int(diff)))
      r_val_old = r_val_new
      which = clamp(which + diff, 0, 2)
      show_settings_menu(which)

# Screen management for the main menu
def show_main_menu(which):
  str_set = "    "
  str_test = "    "
  str_help = "    "
  if which == 0: str_set = " ==>"
  if which == 1: str_test = " ==>"
  if which == 2: str_help = " ==>"
  oled.fill(0)
  oled.text("MegaMosquito's",5,5)
  oled.text("Servo Tester",5,15)
  oled.text(str_set + " Settings",5,30)
  oled.text(str_test + " ServoTest",5,40)
  oled.text(str_help + " Help",5,50)
  oled.show()

# Power LED is just an indicator the Pico has booted up, so turn it on.
pwm_power.duty_u16(1500)

# Loop forever presenting the welcome menu
r_val_old = r.value()
which = 0
show_main_menu(which)
while True:
  sleep_ms(50)
  pwm_green.duty_u16(PWM_OFF)
  pwm_blue.duty_u16(PWM_OFF)
  # Blue button is the "select" button.
  if button_pressed(button_blue):
    debug("BUTTON_BLUE (\"select\")")
    if which == 0:
      settings()
    elif which == 1:
      run_test()
    else:
      # Display the help message
      oled.fill(0)
      oled.text("MegaMosquito's",5,5)
      oled.text("Servo Tester",5,15)
      oled.text("YELLOW = Back",5,30)
      oled.text("BLUE = Select/",5,40)
      oled.text("       Enable",5,50)
      oled.show()
      # Yellow button is the "go back" button.
      while not button_pressed(button_yellow):
        sleep_ms(50)
      debug("BUTTON_YELLOW (\"go back\")")
    show_main_menu(which)
  # Manage the rotary encoder and select setting, test, or help.
  r_val_new = r.value()
  if r_val_old != r_val_new:
    diff = r_val_old - r_val_new
    #debug("--> diff == " + str(int(diff)))
    r_val_old = r_val_new
    which = clamp(which + diff, 0, 2)
    show_main_menu(which)


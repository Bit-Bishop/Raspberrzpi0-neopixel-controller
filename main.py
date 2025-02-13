# led_sign_modes.py
#
# MicroPython script for Raspberry Pi Zero W controlling a NeoPixel LED sign.
#
# The sign “AWARENESS” is split into individual letters so you can manually configure
# which LED indices belong to each letter.
#
# Three modes are provided:
#   1. Fade Letters Mode: Each letter fades in/out in its own color.
#   2. Wave Effect Mode: A warm white base with a moving highlight wave (blue, green, yellow).
#   3. Cycle Colors Mode: The entire sign uniformly cycles through different hues.
#
# The mode automatically switches every 10 minutes.
#

import machine
import neopixel
import time
import math
import random

# -----------------------------
# Hardware & LED Configuration
# -----------------------------

# Set the GPIO pin connected to the NeoPixels (GPIO18 is common).
LED_PIN_NUMBER = 18
LED_PIN = machine.Pin(LED_PIN_NUMBER, machine.Pin.OUT)

# Manual configuration for each letter.
# Edit the "leds" lists below to change which LED indices belong to that letter.
# In this example the sign spells "AWARENESS" (9 letters) and each letter uses 19 LEDs.
letter_configs = [
    {"letter": "A", "leds": list(range(0, 19))},
    {"letter": "W", "leds": list(range(19, 38))},
    {"letter": "A", "leds": list(range(38, 57))},
    {"letter": "R", "leds": list(range(57, 76))},
    {"letter": "E", "leds": list(range(76, 95))},
    {"letter": "N", "leds": list(range(95, 114))},
    {"letter": "E", "leds": list(range(114, 133))},
    {"letter": "S", "leds": list(range(133, 152))},
    {"letter": "S", "leds": list(range(152, 171))}
]

# Determine the total number of LEDs (assumes your LED indices cover 0..NUM_LEDS-1)
NUM_LEDS = 0
for cfg in letter_configs:
    if cfg["leds"]:
        max_led = max(cfg["leds"])
        if max_led + 1 > NUM_LEDS:
            NUM_LEDS = max_led + 1

# Initialize the NeoPixel strip.
np = neopixel.NeoPixel(LED_PIN, NUM_LEDS)

# -----------------------------
# Helper Functions
# -----------------------------

def clear_strip():
    """Turn off all LEDs."""
    for i in range(NUM_LEDS):
        np[i] = (0, 0, 0)
    np.write()

def blend_color(c1, c2, factor):
    """
    Blend two colors.
    
    :param c1: Base color (R,G,B)
    :param c2: Highlight color (R,G,B)
    :param factor: Blend factor (0.0 returns c1, 1.0 returns c2)
    :return: Blended (R,G,B) tuple.
    """
    r = int((1 - factor) * c1[0] + factor * c2[0])
    g = int((1 - factor) * c1[1] + factor * c2[1])
    b = int((1 - factor) * c1[2] + factor * c2[2])
    return (r, g, b)

def hsv_to_rgb(h, s, v):
    """
    Convert HSV color space to RGB.
    
    :param h: Hue in degrees [0, 360)
    :param s: Saturation [0, 1]
    :param v: Value [0, 1]
    :return: (R,G,B) with 0-255 values.
    """
    h = float(h)
    s = float(s)
    v = float(v)
    c = v * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = v - c
    if 0 <= h < 60:
        rp, gp, bp = c, x, 0
    elif 60 <= h < 120:
        rp, gp, bp = x, c, 0
    elif 120 <= h < 180:
        rp, gp, bp = 0, c, x
    elif 180 <= h < 240:
        rp, gp, bp = 0, x, c
    elif 240 <= h < 300:
        rp, gp, bp = x, 0, c
    else:
        rp, gp, bp = c, 0, x
    r = int((rp + m) * 255)
    g = int((gp + m) * 255)
    b = int((bp + m) * 255)
    return (r, g, b)

# -----------------------------
# Display Modes
# -----------------------------

def mode_fade_letters(duration_ms):
    """
    Mode 1: Each letter fades in and out in its own color.
    
    The base colors are set via a color_map (feel free to change them).
    Each letter instance is given a random phase offset so that their fade
    cycles are staggered.
    """
    start_time = time.ticks_ms()
    # Define base colors for each letter (defaulting to white if not found).
    color_map = {
        "A": (255, 0, 0),     # red
        "W": (0, 255, 0),     # green
        "R": (0, 0, 255),     # blue
        "E": (255, 255, 0),   # yellow
        "N": (0, 255, 255),   # cyan
        "S": (255, 0, 255)    # magenta
    }
    # Set up parameters for each letter.
    letter_params = []
    for cfg in letter_configs:
        base_color = color_map.get(cfg["letter"], (255, 255, 255))
        phase_offset = random.uniform(0, 2 * math.pi)
        letter_params.append({"base_color": base_color, "phase_offset": phase_offset})
    
    period = 5.0  # seconds for a full fade cycle
    while time.ticks_diff(time.ticks_ms(), start_time) < duration_ms:
        current_time = time.ticks_ms()
        t = (current_time - start_time) / 1000.0  # elapsed seconds
        # Update each letter
        for idx, cfg in enumerate(letter_configs):
            params = letter_params[idx]
            # Calculate brightness oscillating between 0 and 1
            brightness = (math.sin(2 * math.pi * (t / period) + params["phase_offset"]) + 1) / 2
            scaled_color = (
                int(params["base_color"][0] * brightness),
                int(params["base_color"][1] * brightness),
                int(params["base_color"][2] * brightness)
            )
            # Set all LEDs for this letter
            for led in cfg["leds"]:
                np[led] = scaled_color
        np.write()
        time.sleep(0.05)

def mode_wave_effect(duration_ms):
    """
    Mode 2: Every LED is set to a warm white with a moving color wave.
    
    A wave of color (cycling through blue, green, and yellow) moves along the strip
    approximately every 10 seconds. LEDs close to the wave's current position are blended
    with the wave color.
    """
    start_time = time.ticks_ms()
    warm_white = (255, 244, 229)
    wave_colors = [(0, 0, 255), (0, 255, 0), (255, 255, 0)]  # blue, green, yellow
    wave_period_ms = 10000  # 10 seconds for one full traverse
    threshold = 3  # affect LEDs within this distance from the wave center
    while time.ticks_diff(time.ticks_ms(), start_time) < duration_ms:
        current_time = time.ticks_ms()
        # Compute wave position along the LED strip
        phase = (current_time % wave_period_ms) / wave_period_ms  # 0.0 to 1.0
        wave_pos = phase * NUM_LEDS
        # Choose a wave color (here using the wave position mod the number of colors)
        wave_color = wave_colors[int(wave_pos) % len(wave_colors)]
        for i in range(NUM_LEDS):
            distance = abs(i - wave_pos)
            if distance < threshold:
                # Closer to the wave center means a higher blend factor.
                factor = 1 - (distance / threshold)
                color = blend_color(warm_white, wave_color, factor)
            else:
                color = warm_white
            np[i] = color
        np.write()
        time.sleep(0.05)

def mode_cycle_colors(duration_ms):
    """
    Mode 3: The entire sign uniformly cycles through colours.
    
    A hue is computed based on the elapsed time and applied to all LEDs. The sign
    will slowly change its color over time.
    """
  

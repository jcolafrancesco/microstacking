# Microstacking

Microstacking is a project that allows you to control a camera and a stepper motor for focus stacking in a microscopy context. The application is built using Python and Tkinter for the GUI, and an Arduino for controlling the stepper motor.

## Features

- Control camera settings such as shutter speed, ISO, white balance, and image format.
- Capture images and display them in a treeview.
- Control a stepper motor for precise focus stacking.
- Preview camera feed.
- Save captured images to a specified folder.

## Requirements

- Python 3.x
- Tkinter
- ttkthemes
- PIL (Pillow)
- gphoto2
- pyserial
- Arduino with A4988 stepper motor driver

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/microstacking.git
    cd microstacking
    ```

2. Install the required Python packages:
    ```bash
    pip install tk ttkthemes pillow gphoto2 pyserial
    ```

3. Upload the Arduino firmware to your Arduino board:
    ```bash
    cd firmware
    arduino --upload stepper_firmware.ino
    ```

## Usage

1. Connect your camera and Arduino to your computer.
2. Run the Python application:
    ```bash
    python microstacking.py
    ```

## Video Demonstration

[![Microstacking Video](https://img.youtube.com/vi/_M9yZgYWU7Y/0.jpg)](https://www.youtube.com/watch?v=_M9yZgYWU7Y)
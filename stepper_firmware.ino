/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 *
 * Copyright 2024 Julien Colafrancesco
 */

#include "A4988.h" // From here: https://github.com/laurb9/StepperDriver

// using a 200-step motor (most common)
#define MOTOR_STEPS 200
// configure the pins connected
#define STEP 3
#define DIR 6
#define ENABLE_PIN 8

A4988 stepper(MOTOR_STEPS, DIR, STEP);

#define MICROSTEPS 1
#define MOTOR_X_RPM 30

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(10); // Sets the maximum milliseconds to wait for serial data
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, HIGH);
  pinMode(DIR, OUTPUT);
  stepper.begin(MOTOR_X_RPM, MICROSTEPS);
}

void loop() {
    if (Serial.available() > 0) {
        char command = Serial.read();
        if (command == 'U' || command == 'D') {
            while (Serial.available() == 0) {} // Wait for the integer value
            int value = Serial.parseInt();
            if (command == 'U') {
                stepper.rotate(value);
            } else if (command == 'D') {
                stepper.rotate(-value);
            }
        } else if (command == 'R') {
            digitalWrite(ENABLE_PIN, HIGH);
        } else if (command == 'A') {
            digitalWrite(ENABLE_PIN, LOW);
        }
    }
}


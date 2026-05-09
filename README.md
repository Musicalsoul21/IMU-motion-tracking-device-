# IMU-motion-tracking-device
Standalone Multi-Node IMU Motion Tracking System for Clinical Rehabilitation
# Standalone Multi-Node Wireless Motion Tracking Device
### IMU Calibration Validation System — Arduino Uno + STM32 WB55RG + BNO055

> **Project:** Standalone Kinematic Data Acquisition System for Clinical Rehabilitation Monitoring  
> **Supervisor:** Prof. Nelson Rosa  
> **Author:** Ananya  
> **Last Updated:** May 2026

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Hardware Required](#hardware-required)
3. [Software Versions](#software-versions)
4. [Library Installation](#library-installation)
5. [Arduino IDE Settings](#arduino-ide-settings)
6. [Pin Connections — Arduino Uno (Servo Rig)](#pin-connections--arduino-uno-servo-rig)
7. [Pin Connections — STM32 WB55RG Node](#pin-connections--stm32-wb55rg-node)
8. [Power Wiring — TP4056 + LiPo + AMS1117](#power-wiring--tp4056--lipo--ams1117)
9. [File Structure](#file-structure)
10. [How to Run the Experiment](#how-to-run-the-experiment)
11. [Python Setup & Analysis](#python-setup--analysis)
12. [Known Issues & Updates Needed](#known-issues--updates-needed)
13. [LED Blink Codes — STM32](#led-blink-codes--stm32)
14. [Troubleshooting](#troubleshooting)

---

## System Overview

```
Arduino Uno (USB → Laptop)          STM32 WB55RG Node #1 (Battery)
┌─────────────────────┐             ┌──────────────────────────────┐
│  Pin 9  → Servo 1   │             │  I2C  → BNO055 IMU #1        │
│  Pin 10 → Servo 2   │             │  SPI  → MicroSD Card #1      │
│  USB → Python Logger│             │  3.3V → STM32 → LiPo+TP4056│
└─────────────────────┘             └──────────────────────────────┘
         │                          STM32 WB55RG Node #2 (Battery)
         │ Serial @ 115200 baud     ┌──────────────────────────────┐
         ▼                          │  I2C  → BNO055 IMU #2        │
   servo1_log.csv                   │  SPI  → MicroSD Card #2      │
   servo2_log.csv                   │  3.3V → STM32 → LiPo+TP4056│
   (Python captures)                └──────────────────────────────┘
                                              │
                                    S1001.CSV / S2001.CSV
                                    (copy from SD card)
                                              │
                                              ▼
                                    analyze_validation.py
                                    (VS Code / Python)
```

---

## Hardware Required

| # | Component | Qty | Notes |
|---|-----------|-----|-------|
| 1 | Arduino Uno (ELEGOO UNO R3 or genuine) | 1 | Servo controller only |
| 2 | STM32 WB55RG Nucleo-64 (P-Nucleo WB55RG) | 2 | One per IMU node |
| 3 | Adafruit BNO055 IMU Breakout | 2 | I2C address 0x28 |
| 4 | Adafruit MicroSD SPI Breakout Board+ | 2 | SPI interface |
| 5 | SanDisk Industrial MicroSD 16 GB | 2 | FAT32 formatted |
| 6 | TowerPro SG92R Micro Servo | 2 | Swing + Twist axes |
| 7 | 3.7V 500 mAh Li-Po Battery | 2 | One per node |
| 8 | TP4056 USB-C Charging Module (with DW01A) | 2 | Protection IC required |
| 9 | 100 µF Electrolytic Capacitor | 2 | AMS1117 output decoupling |
| 10 | 4.7 kΩ Resistor | 4 | I2C pull-ups (2 per node) |
| 11 | FR4 Protoboard | 2 | For PDB assembly |
| 12 | ST-Link V2 Debugger | 1 | STM32 firmware flashing |
| 13 | USB-A to USB-B cable | 1 | Arduino → Laptop |
| 14 | Jumper wires (AWG 24/26) | — | Power + signal wiring |

---

## Software Versions

### Arduino IDE
```
Arduino IDE Version:    2.3.x or later
  Download: https://www.arduino.cc/en/software

STMicroelectronics STM32 Board Package: 2.x
  (installed via Boards Manager — see below)

Arduino AVR Boards (for Arduino Uno):  1.8.x
  (pre-installed with Arduino IDE)
```

### Python (for analysis scripts)
```
Python Version:         3.10 or later
  Download: https://www.python.org/downloads/

VS Code Version:        1.88 or later
  Download: https://code.visualstudio.com/

VS Code Extensions:
  - Python (Microsoft)     v2024.x
  - Pylance (Microsoft)    v2024.x
```

### ST-Link Utility / STM32CubeProgrammer
```
STM32CubeProgrammer:    2.x
  Download: https://www.st.com/en/development-tools/stm32cubeprog.html
  (Required for initial STM32 firmware flash if ST-Link not auto-detected)
```

---

## Library Installation

### Step 1 — Add STM32 Board Package to Arduino IDE

1. Open Arduino IDE
2. Go to **File → Preferences**
3. In **Additional Boards Manager URLs**, paste:
   ```
   https://github.com/stm32duino/BoardManagerFiles/raw/main/package_stmicroelectronics_index.json
   ```
4. Click **OK**
5. Go to **Tools → Board → Boards Manager**
6. Search: `STM32`
7. Install: **STM32 MCU based boards** by STMicroelectronics
8. Wait for installation to complete (~5 minutes)

---

### Step 2 — Install Arduino Libraries

Open Arduino IDE → **Tools → Manage Libraries** → search and install each:

| Library Name | Author | Version | Used By |
|---|---|---|---|
| `Adafruit BNO055` | Adafruit | ≥ 1.6.3 | STM32 firmware |
| `Adafruit Unified Sensor` | Adafruit | ≥ 1.1.14 | STM32 firmware (dependency) |
| `SD` | Arduino | ≥ 1.2.4 | STM32 firmware |
| `SPI` | Arduino | built-in | STM32 firmware |
| `Wire` | Arduino | built-in | STM32 firmware |
| `Servo` | Arduino | ≥ 1.2.1 | Arduino Uno firmware |

> ⚠️ **Important:** `Adafruit Unified Sensor` MUST be installed — it is a required dependency of `Adafruit BNO055`. The IDE will warn you if it is missing.

---

### Step 3 — Install Python Libraries

Open **VS Code Terminal** (or any terminal with Python) and run:

```bash
pip install pyserial pandas numpy matplotlib scipy
```

| Package | Version | Purpose |
|---|---|---|
| `pyserial` | ≥ 3.5 | Arduino Serial port capture |
| `pandas` | ≥ 2.0 | CSV loading and data manipulation |
| `numpy` | ≥ 1.26 | RMSE, statistics, cross-correlation |
| `matplotlib` | ≥ 3.8 | Validation plot generation |
| `scipy` | ≥ 1.12 | Signal interpolation and alignment |

Verify installation:
```bash
python -c "import serial, pandas, numpy, matplotlib, scipy; print('All OK')"
```

---

## Arduino IDE Settings

### For STM32 WB55RG Nodes

Go to **Tools** menu and set each option exactly as shown:

```
Board:                  STM32 MCU based boards
                        → Nucleo-64

Board part number:      P-Nucleo WB55RG        ← CRITICAL

Optimize:               Smallest (-Os default)  ← CRITICAL (prevents Flash overflow)

C Runtime Library:      Newlib Nano (default)

Debug symbols:          None

U(S)ART support:        Enabled (generic 'Serial')

USB support:            None

Upload method:          Mass Storage           ← or STLink if ST-Link connected

Port:                   (not required for Mass Storage upload)
```

> ⚠️ **If you get "FLASH overflowed" error:** Ensure Optimize is set to `Smallest (-Os default)` AND the board is exactly `P-Nucleo WB55RG`. Wrong board = wrong Flash map.

---

### For Arduino Uno (Servo Rig)

```
Board:                  Arduino AVR Boards → Arduino Uno

Port:                   COM3 (Windows) or /dev/ttyACM0 (Mac/Linux)
                        ← Check Device Manager for exact port

Programmer:             AVRISP mkII (default)

Baud Rate:              115200 (must match Serial.begin in code)
```

---

## Pin Connections — Arduino Uno (Servo Rig)

```
Arduino Uno
┌─────────────────────────────────────────────────────┐
│                                                     │
│  Pin  9 (PWM) ──────────────────► Servo 1 Signal   │
│  Pin 10 (PWM) ──────────────────► Servo 2 Signal   │
│                                                     │
│  5V   ──────────────────────────► Servo 1 VCC  (+) │
│  5V   ──────────────────────────► Servo 2 VCC  (+) │
│  GND  ──────────────────────────► Servo 1 GND  (-) │
│  GND  ──────────────────────────► Servo 2 GND  (-) │
│                                                     │
│  USB-B ─────────────────────────► Laptop USB-A     │
│  (powers Arduino + Serial data)                     │
└─────────────────────────────────────────────────────┘
```

### Servo Wire Colours (SG92R)
```
Orange  →  Signal  →  Pin 9 or Pin 10
Red     →  VCC     →  Arduino 5V
Brown   →  GND     →  Arduino GND
```

> ⚠️ **Do NOT power servos from 3.3V** — they require 4.8–6V. Use the Arduino 5V rail (USB-powered).  
> ⚠️ **Do NOT connect Arduino to STM32** — they are completely independent systems with separate power sources.

---

## Pin Connections — STM32 WB55RG Node

> Same wiring applies to BOTH Node #1 and Node #2. Only the firmware FILE_PREFIX changes (S1 vs S2).

### BNO055 IMU → STM32 (I2C)

```
BNO055 Breakout              STM32 WB55RG Nucleo
┌─────────────┐              ┌──────────────────────────────┐
│             │              │                              │
│  VIN  ──────┼──────────────┼► 3.3V  (CN10, Pin 4)        │
│  GND  ──────┼──────────────┼► GND   (CN10, Pin 6)        │
│  SDA  ──────┼──4.7kΩ──3V3──┼► PB9   (CN10, Pin 5) I2C1   │
│  SCL  ──────┼──4.7kΩ──3V3──┼► PB8   (CN10, Pin 3) I2C1   │
│  ADR  ──────┼── GND        │  (I2C address = 0x28)       │
│  INT  ──────┼── NC          │  (not used)                 │
└─────────────┘              └──────────────────────────────┘
```

> ⚠️ **Pull-up resistors are required:** 4.7 kΩ from SDA to 3.3V and SCL to 3.3V. The BNO055 breakout board includes onboard pull-ups on most Adafruit versions — check your breakout board. If I2C fails, add external 4.7 kΩ resistors.

### MicroSD Breakout → STM32 (SPI)

```
MicroSD Breakout             STM32 WB55RG Nucleo
┌─────────────┐              ┌──────────────────────────────┐
│             │              │                              │
│  VCC  ──────┼──────────────┼► 3.3V  (CN10, Pin 4)        │
│  GND  ──────┼──────────────┼► GND   (CN10, Pin 6)        │
│  CLK  ──────┼──────────────┼► PA5   (CN10, Pin 11) SPI1  │
│  DO   ──────┼──────────────┼► PA6   (CN10, Pin 13) SPI1  │
│  DI   ──────┼──────────────┼► PA7   (CN10, Pin 15) SPI1  │
│  CS   ──────┼──────────────┼► PA4   (CN7,  Pin 17) SPI1  │
└─────────────┘              └──────────────────────────────┘
```

> SPI clock configured at **10 MHz** in firmware (`SPI.begin()` default on STM32duino).

### Full STM32 Pin Summary Table

| STM32 Pin | Connector | Function | Connected To |
|-----------|-----------|----------|--------------|
| PB9 | CN10 Pin 5 | I2C1 SDA | BNO055 SDA |
| PB8 | CN10 Pin 3 | I2C1 SCL | BNO055 SCL |
| PA4 | CN7 Pin 17 | SPI1 CS | MicroSD CS |
| PA5 | CN10 Pin 11 | SPI1 SCK | MicroSD CLK |
| PA6 | CN10 Pin 13 | SPI1 MISO | MicroSD DO |
| PA7 | CN10 Pin 15 | SPI1 MOSI | MicroSD DI |
| 3V3 | CN10 Pin 4 | 3.3V supply | BNO055 VIN + SD VCC |
| GND | CN10 Pin 6 | Ground | BNO055 GND + SD GND + AMS1117 GND |
| VIN | CN10 Pin 8 | Battery input | AMS1117 OUT (3.3V regulated) |

---

## Power Wiring — TP4056 + LiPo + AMS1117

```
LiPo Battery 3.7V
┌─────────────────┐
│  + (Red)  ──────┼──────────────► TP4056  B+
│  - (Black)──────┼──────────────► TP4056  B-
└─────────────────┘

TP4056 Module
┌─────────────────┐
│  B+  ◄──────────┼── LiPo +
│  B-  ◄──────────┼── LiPo -
│  OUT+────────────┼──────────────► AMS1117  IN
│  OUT-────────────┼──────────────► AMS1117  GND
│  USB-C ◄────────┼── USB-C cable (for charging only)
└─────────────────┘

AMS1117-3.3V Regulator
┌─────────────────┐
│  IN  ◄──────────┼── TP4056 OUT+
│  GND ◄──────────┼── TP4056 OUT-  ──► STM32 GND
│  OUT─────────────┼──────────────► STM32 3V3 pin (CN10 Pin 4)
│       ├─────────100µF cap──────► GND  (decoupling)
└─────────────────┘
```

> ⚠️ **Verify AMS1117 output = 3.3V with a multimeter BEFORE connecting to STM32**  
> ⚠️ **Never connect Arduino 5V to STM32 3.3V pins — this will damage the STM32**  
> ⚠️ **TP4056 module MUST have the DW01A protection chip** (6-pad module, not 4-pad)

---

## File Structure

```
project/
│
├── firmware/
│   ├── arduino_servo/
│   │   └── two_servo_validation.ino     ← Upload to Arduino Uno
│   │
│   └── stm32_imu/
│       ├── stm32_node1.ino              ← Upload to STM32 #1 (FILE_PREFIX = "S1")
│       └── stm32_node2.ino              ← Upload to STM32 #2 (FILE_PREFIX = "S2")
│
├── python/
│   ├── serial_logger.py                 ← Run DURING experiment
│   └── analyze_validation.py           ← Run AFTER experiment
│
├── data/                                ← Create this folder
│   ├── servo1_log.csv                   ← Auto-generated by serial_logger.py
│   ├── servo2_log.csv                   ← Auto-generated by serial_logger.py
│   ├── S1001.CSV                        ← Copy from STM32 #1 SD card
│   └── S2001.CSV                        ← Copy from STM32 #2 SD card
│
├── results/
│   └── validation_report_both.png      ← Auto-generated by analyze_validation.py
│
└── README.md                            ← This file
```

---

## How to Run the Experiment

### Step 1 — Prepare SD Cards
```
1. Insert MicroSD cards into a laptop card reader
2. Format each card as FAT32
   Windows: right-click → Format → FAT32
   Mac:     Disk Utility → Erase → MS-DOS (FAT)
3. Insert formatted cards back into STM32 SD breakout boards
```

### Step 2 — Upload Firmware to STM32 Nodes

```
Node #1:
  1. Open stm32_node1.ino in Arduino IDE
  2. Verify FILE_PREFIX = "S1" at line 8
  3. Settings: P-Nucleo WB55RG, Smallest (-Os), Mass Storage
  4. Connect STM32 via USB
  5. Click Upload (→)
  6. Wait for "Upload complete"
  7. Disconnect USB — Node #1 will be powered by battery

Node #2:
  1. Open stm32_node2.ino in Arduino IDE
  2. Verify FILE_PREFIX = "S2" at line 8
  3. Same settings as Node #1
  4. Upload → Disconnect
```

### Step 3 — Upload Firmware to Arduino Uno

```
1. Open two_servo_validation.ino in Arduino IDE
2. Settings: Arduino Uno, correct COM port
3. Click Upload (→)
4. DO NOT open Serial Monitor after upload
   (Python needs the COM port — only one can use it at a time)
5. Leave Arduino USB connected to laptop
```

### Step 4 — Edit Python Serial Logger

```python
# Open python/serial_logger.py in VS Code
# Change line 7 to your Arduino COM port:

PORT = 'COM3'        # Windows example
# PORT = 'COM5'      # another Windows example
# PORT = '/dev/ttyACM0'   # Linux
# PORT = '/dev/tty.usbmodem14101'  # Mac
```

**Find your COM port:**
- **Windows:** Device Manager → Ports (COM & LPT) → USB Serial Device (COMx)
- **Mac:** `ls /dev/tty.*` in terminal
- **Linux:** `ls /dev/ttyACM*` or `ls /dev/ttyUSB*`

### Step 5 — Run the Experiment

```
TERMINAL 1 (VS Code):
  cd project/python
  python serial_logger.py

  → You will see:
     Opening COM3 at 115200 baud...
     Waiting for Arduino to start...

THEN immediately:
  Power ON STM32 Node #1  →  wait for 6 fast blinks
  Power ON STM32 Node #2  →  wait for 6 fast blinks

The Arduino was already plugged in (Step 3).
It resets automatically when Python opens the serial port.

  → Terminal will show:
     timestamp_ms,cycle,direction,commanded_deg
     # HOLDING_AT_ZERO
     # SWEEP_START
     515,0,FWD,0
     1030,0,FWD,5
     ...
     → Logged 10 servo steps...

WAIT for all 5 cycles to complete (~5 minutes):
  → TEST_COMPLETE printed → Python stops automatically
  → servo1_log.csv and servo2_log.csv saved in data/ folder
```

### Step 6 — Collect STM32 Data

```
1. Wait for STM32 LED to blink SLOWLY (1 second on/off)
   This means: test complete, file closed, safe to remove SD
   
2. Power OFF both STM32 nodes

3. Remove MicroSD cards

4. Copy S1001.CSV → project/data/S1001.CSV
   Copy S2001.CSV → project/data/S2001.CSV
```

### Step 7 — Run Analysis

```bash
cd project/python
python analyze_validation.py
```

```
Output:
  → Prints RMSE, hysteresis, pass/fail to terminal
  → Saves validation_report_both.png to results/ folder
  → Opens interactive plot window
```

---

## Python Setup & Analysis

### Configure File Paths

Open `analyze_validation.py` and verify the file paths at the top match your folder:

```python
# ── CONFIG ─────────────────────────────────────
SERVO1_FILE = '../data/servo1_log.csv'
SERVO2_FILE = '../data/servo2_log.csv'
IMU1_FILE   = '../data/S1001.CSV'
IMU2_FILE   = '../data/S2001.CSV'
FULL_RANGE  = 180.0        # degrees
LIMIT_PCT   = 2.5          # pass/fail threshold %
```

### If Euler Angle Wrapping Occurs (Servo 2)

If Servo 2 plots show angles going beyond 180° or errors in the hundreds of degrees, add this unwrapping fix in `analyze_validation.py` after loading IMU data:

```python
import numpy as np

# Unwrap Euler angles to remove 0°/360° boundary jumps
for axis in ['euler_x_deg', 'euler_y_deg', 'euler_z_deg']:
    imu2[axis] = np.degrees(np.unwrap(np.radians(imu2[axis])))
```

### Check Which IMU Axis to Use

If correlation is weak, manually print axis ranges to identify the correct one:

```python
for axis in ['euler_x_deg', 'euler_y_deg', 'euler_z_deg']:
    rng = imu1[axis].max() - imu1[axis].min()
    print(f"IMU1 {axis}: range = {rng:.1f}°")

# The axis with range closest to 180° = correct axis
```

---

## Known Issues & Updates Needed

### Hardware Issues

| Issue | Status | Fix |
|-------|--------|-----|
| PDB dimensions 150×150 mm (target 100×100 mm) | ⚠️ Known | Custom PCB in next revision — cut board BEFORE soldering |
| No hardware sync between Arduino and STM32 | ⚠️ Known | Use cross-correlation in Python (implemented) |
| AMS1117 linear regulator — low efficiency | ⚠️ Known | Replace with switching regulator (TPS63020) in future |
| Jumper wires increase node height to ~35 mm | ⚠️ Known | Custom PCB with surface-mount components |

### Firmware Updates Needed

| Update | Priority | Description |
|--------|----------|-------------|
| Low-power sleep between samples | 🔴 High | Implement STOP 1 mode — reduces current from 10 mA to ~2 µA between 10ms windows, extends battery to 50+ hours |
| Magnetometer NDOF calibration | 🔴 High | Add figure-of-eight calibration routine with EEPROM storage |
| Hardware timestamp sync pulse | 🟡 Medium | GPIO output pulse from STM32 at first sample for precise time alignment |
| STM32 sub-GHz inter-node sync | 🟡 Medium | Use onboard 802.15.4 radio for microsecond node timing |
| SD card flush optimisation | 🟢 Low | Increase flush interval from 10 to 50 rows to reduce SD write spikes |
| BNO085 library integration | 🟢 Low | Add BNO085 support for comparative drift study |

### Software Updates Needed

| Update | Priority | Description |
|--------|----------|-------------|
| Euler angle unwrap in Python | 🔴 High | `np.unwrap()` for axes crossing 0°/360° boundary |
| Automatic COM port detection | 🟡 Medium | Replace hardcoded PORT with `serial.tools.list_ports` auto-detect |
| Real-time plot during capture | 🟡 Medium | Live matplotlib update in serial_logger.py |
| CSV → Excel auto-export | 🟢 Low | Add openpyxl output for formatted Excel report |

---

## LED Blink Codes — STM32

| Pattern | Meaning | Action Required |
|---------|---------|-----------------|
| 3 blinks (repeat) | BNO055 IMU not found | Check I2C wiring, SDA/SCL pull-ups, I2C address (0x28 vs 0x29) |
| 4 blinks (repeat) | SD card initialisation failed | Check SPI wiring, CS pin (PA4), card format (must be FAT32) |
| 5 blinks (repeat) | Log file creation failed | Card full? Re-format card. All 999 filenames used? |
| 6 rapid blinks (once) | ✅ All systems nominal | Logging started — experiment can begin |
| Slow blink 1s on/1s off | Test complete / idle | Safe to power off and remove SD card |

---

## Troubleshooting

### Arduino IDE — Compilation Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `region FLASH overflowed by XXXXX bytes` | Wrong board or optimisation | Set board = P-Nucleo WB55RG, Optimise = Smallest (-Os) |
| `Adafruit_BNO055.h: No such file or directory` | Library not installed | Tools → Manage Libraries → install Adafruit BNO055 |
| `SD.h: No such file or directory` | SD library missing | Should be built-in; reinstall Arduino IDE if missing |
| `'Servo' was not declared` | Wrong board selected | Servo.h only compiles for Arduino boards, not STM32 |
| `Wire not declared` | STM32duino package missing | Boards Manager → install STM32 MCU based boards |

### Python — Runtime Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `serial.serialutil.SerialException` | Wrong COM port or IDE still open | Close Arduino IDE Serial Monitor; check Device Manager for correct port |
| `FileNotFoundError: S1001.CSV` | File not copied from SD card | Copy CSV files from SD card to `data/` folder |
| `KeyError: euler_x_deg` | Old CSV format (short column names) | Check CSV header; update column names in Python config |
| Plot shows angles >180° | Euler angle wrapping | Add `np.unwrap()` — see Python Setup section |
| `ValueError: cannot convert float NaN` | Time alignment failed | Increase logging duration; ensure both devices ran simultaneously |

### Hardware — No LED Activity on STM32

```
1. Check AMS1117 output voltage = 3.3V with multimeter
2. Check TP4056 LED:
   Red  = charging (OK, LiPo was low)
   Blue = fully charged (OK)
   None = no USB-C connected to TP4056 / no battery
3. Check LiPo polarity: red wire to B+, black to B-
4. Try pressing RESET button on Nucleo board
5. Re-flash firmware via ST-Link
```

### BNO055 Always Reads Zero

```
1. Confirm I2C address: AD0 pin to GND = 0x28, to VCC = 0x29
   Check firmware: Adafruit_BNO055 bno(55, 0x28);
2. Confirm SDA and SCL not swapped
3. Confirm 4.7kΩ pull-up resistors on SDA and SCL to 3.3V
4. Confirm VIN connected to 3.3V (NOT 5V)
5. Run I2C scanner sketch to detect device address
```

---

## Quick Reference Card

```
╔══════════════════════════════════════════════════════════════╗
║              QUICK START CHECKLIST                           ║
╠══════════════════════════════════════════════════════════════╣
║ BEFORE EXPERIMENT:                                           ║
║  □ SD cards formatted FAT32                                  ║
║  □ STM32 #1 flashed with S1 prefix                          ║
║  □ STM32 #2 flashed with S2 prefix                          ║
║  □ Arduino Uno flashed with servo code                       ║
║  □ Arduino IDE CLOSED                                        ║
║  □ serial_logger.py COM port updated                         ║
║  □ Servo arms attached and move freely 0°–180°               ║
║  □ BNO055 rigidly mounted on servo rotating arm              ║
║  □ LiPo batteries charged (TP4056 blue LED)                  ║
╠══════════════════════════════════════════════════════════════╣
║ STARTUP ORDER:                                               ║
║  1. python serial_logger.py  (VS Code terminal)              ║
║  2. Power ON STM32 #1 → wait for 6 blinks                   ║
║  3. Power ON STM32 #2 → wait for 6 blinks                   ║
║  4. Arduino already plugged in → auto-resets on Python open  ║
╠══════════════════════════════════════════════════════════════╣
║ AFTER EXPERIMENT:                                            ║
║  □ Wait for STM32 slow blink (safe to remove SD)             ║
║  □ Power OFF both STM32 nodes                                ║
║  □ Copy S1001.CSV and S2001.CSV to data/ folder              ║
║  □ python analyze_validation.py                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Contact & Repository

**Project:** Standalone Multi-Node Wireless Motion Tracking Device  
**Course:** Research Credit Project  
**Supervisor:** Prof. Nelson Rosa  
**Author:** Ananya — May 2026

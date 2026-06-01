# serial_logger.py
# Captures Arduino Serial and splits into TWO csv files
# Records only ONE cycle

import serial
import csv
import time
import sys

# ── CONFIG ────────────────────────────────────
PORT       = 'COM8'      # ← change to your port
BAUD       = 115200
OUT_FILE_1 = 'servo1_log.csv'   # servo on Pin 9
OUT_FILE_2 = 'servo2_log.csv'   # servo on Pin 10
ONLY_CYCLE = 1
# ──────────────────────────────────────────────

print(f"Opening {PORT}...")
print("Plug in Arduino USB to start.\n")

try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
except Exception as e:
    print(f"ERROR: {e}")
    import serial.tools.list_ports
    print("Available ports:")
    for p in serial.tools.list_ports.comports():
        print(f"  {p}")
    sys.exit(1)

rows1 = 0
rows2 = 0
start_time = None
recording_started = False

header = ['pc_time_ms', 'arduino_time_ms',
          'cycle', 'direction', 'commanded_deg']

with open(OUT_FILE_1, 'w', newline='') as f1, \
     open(OUT_FILE_2, 'w', newline='') as f2:

    writer1 = csv.writer(f1)
    writer2 = csv.writer(f2)
    writer1.writerow(header)
    writer2.writerow(header)

    try:
        while True:
            line = ser.readline().decode('utf-8',
                                         errors='ignore').strip()
            if not line:
                continue

            print(line)

            if line.startswith('#') or line.startswith('servo_id'):
                if 'TEST_COMPLETE' in line:
                    print("\nTest complete!")
                    break
                continue

            # Parse: servo_id,timestamp,cycle,direction,angle
            if ',' in line:
                parts = line.split(',')
                if len(parts) == 5:
                    try:
                        servo_id   = int(parts[0])
                        arduino_ms = int(parts[1])
                        cycle      = int(parts[2])
                        direction  = parts[3].strip()
                        angle      = int(parts[4])

                        # Start only when cycle 1 appears
                        if cycle == ONLY_CYCLE:
                            recording_started = True
                        elif recording_started:
                            print("\nOne cycle captured. Stopping.")
                            break
                        else:
                            continue

                        if start_time is None:
                            start_time = time.time()

                        pc_ms = int((time.time() -
                                     start_time) * 1000)

                        row = [pc_ms, arduino_ms,
                               cycle, direction, angle]

                        if servo_id == 1:
                            writer1.writerow(row)
                            rows1 += 1
                        elif servo_id == 2:
                            writer2.writerow(row)
                            rows2 += 1

                        if (rows1 + rows2) % 20 == 0:
                            print(f"  Servo1: {rows1} steps  "
                                  f"Servo2: {rows2} steps")

                    except ValueError:
                        pass

    except KeyboardInterrupt:
        print("\nStopped by user.")

ser.close()
print(f"\nservo1_log.csv -> {rows1} rows")
print(f"servo2_log.csv -> {rows2} rows")

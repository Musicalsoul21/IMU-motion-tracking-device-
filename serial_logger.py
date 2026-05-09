import serial
import time
import sys

# ══════════════════════════════════════════
#  CHANGE THIS TO YOUR PORT
PORT     = 'COM8'        # yours is COM8
BAUD     = 115200
# ══════════════════════════════════════════

# Save CSV right next to this script
import os
SAVE_FOLDER = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE   = os.path.join(SAVE_FOLDER, 'servo_log.csv')

print("=" * 50)
print(f"Port:      {PORT}")
print(f"Saving to: {SAVE_FILE}")
print("=" * 50)

# Open serial port
try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    print(f"✅ Serial port opened!")
except Exception as e:
    print(f"❌ Cannot open {PORT}: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

# Open CSV file immediately — write mode
try:
    csv_file = open(SAVE_FILE, 'w')
    csv_file.write("arduino_time_ms,cycle,direction,commanded_deg\n")
    csv_file.flush()
    print(f"✅ CSV file created!")
except Exception as e:
    print(f"❌ Cannot create CSV: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

print("\nWaiting for Arduino... (plug in USB or press Reset)\n")

rows   = 0
errors = 0

try:
    while True:
        # Read one line
        try:
            raw  = ser.readline()
            line = raw.decode('utf-8', errors='ignore').strip()
        except Exception:
            continue

        if not line:
            continue

        # Always print everything to terminal
        print(line)

        # Skip comment lines and headers
        if line.startswith('#'):
            # Check for test complete
            if 'TEST_COMPLETE' in line:
                print("\n✅ Test complete!")
                break
            continue

        if line.startswith('timestamp') or line.startswith('SYNC'):
            continue

        # Try to parse data line: 4049,0,FWD,0
        if ',' in line:
            parts = line.split(',')
            if len(parts) == 4:
                try:
                    t   = int(parts[0].strip())
                    c   = int(parts[1].strip())
                    d   = parts[2].strip()
                    ang = int(parts[3].strip())

                    # Write to CSV immediately
                    csv_file.write(f"{t},{c},{d},{ang}\n")
                    csv_file.flush()  # save instantly
                    rows += 1

                    if rows % 10 == 0:
                        print(f"  ✅ {rows} rows saved to CSV")

                except ValueError as e:
                    errors += 1
                    # not a data line, skip silently

except KeyboardInterrupt:
    print("\n⚠️  Stopped by Ctrl+C")

finally:
    # Always close properly
    csv_file.flush()
    csv_file.close()
    ser.close()
    print(f"\n{'='*50}")
    print(f"DONE!")
    print(f"Rows saved:  {rows}")
    print(f"Saved to:    {SAVE_FILE}")
    print(f"{'='*50}")
    input("\nPress Enter to exit...")
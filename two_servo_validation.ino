#include <Servo.h>

// ── Two Servos ─────────────────────────────────
Servo servo1;   // Pin 9  — Axis 1 (e.g. Swing)
Servo servo2;   // Pin 10 — Axis 2 (e.g. Twist)

const int SERVO1_PIN    = 9;
const int SERVO2_PIN    = 10;

// ── Test Config ────────────────────────────────
const int STEP_DEG      = 5;
const int STEP_DELAY_MS = 500;
const int SETTLE_MS     = 50;
const int PAUSE_MS      = 2000;
const int NUM_CYCLES    = 5;

// ─────────────────────────────────────────────────────
void logStep(int servoID, unsigned long ts, 
             int cycle, const char* dir, int pos) {
  // Format: SERVO_ID, timestamp, cycle, direction, angle
  Serial.print(servoID);   Serial.print(",");
  Serial.print(ts);        Serial.print(",");
  Serial.print(cycle);     Serial.print(",");
  Serial.print(dir);       Serial.print(",");
  Serial.println(pos);
}

// ─────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);

  // Both start at 0°
  servo1.write(0);
  servo2.write(0);
  delay(1000);

  // CSV header — both servos in same Serial stream
  // Python will split by servo_id column
  Serial.println("servo_id,timestamp_ms,cycle,direction,commanded_deg");

  // Hold at 0° so IMUs settle — gives alignment marker
  Serial.println("# HOLDING_AT_ZERO");
  delay(3000);

  Serial.println("# SWEEP_START");
}

// ─────────────────────────────────────────────────────
void loop() {
  static int cycle = 0;

  if (cycle >= NUM_CYCLES) {
    servo1.write(0);
    servo2.write(0);
    Serial.println("# TEST_COMPLETE");
    while (true);
  }

  Serial.print("# CYCLE ");
  Serial.println(cycle);

  // ── Forward Sweep: 0° → 180° ──────────────────
  // Both servos move TOGETHER, same step, same time
  for (int pos = 0; pos <= 180; pos += STEP_DEG) {

    servo1.write(pos);
    servo2.write(pos);
    delay(SETTLE_MS);  // both settle together

    unsigned long ts = millis();

    // Log both in same timestamp window
    logStep(1, ts, cycle, "FWD", pos);
    logStep(2, ts, cycle, "FWD", pos);

    delay(STEP_DELAY_MS - SETTLE_MS);
  }

  Serial.println("# PAUSE_180");
  delay(PAUSE_MS);

  // ── Backward Sweep: 180° → 0° ─────────────────
  for (int pos = 180; pos >= 0; pos -= STEP_DEG) {

    servo1.write(pos);
    servo2.write(pos);
    delay(SETTLE_MS);

    unsigned long ts = millis();

    logStep(1, ts, cycle, "BWD", pos);
    logStep(2, ts, cycle, "BWD", pos);

    delay(STEP_DELAY_MS - SETTLE_MS);
  }

  Serial.println("# PAUSE_0");
  delay(PAUSE_MS);

  cycle++;
}
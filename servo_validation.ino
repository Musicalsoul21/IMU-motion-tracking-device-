#include <Servo.h>

Servo myServo;

const int SERVO_PIN     = 9;
const int STEP_DEG      = 10;
const int STEP_DELAY_MS = 500;
const int SETTLE_MS     = 50;
const int PAUSE_MS      = 2000;
const int NUM_CYCLES    = 5;

void setup() {
  Serial.begin(115200);
  myServo.attach(SERVO_PIN);
  myServo.write(0);
  delay(1000);

  // Print CSV header
  Serial.println("timestamp_ms,cycle,direction,commanded_deg");
  
  // Hold at 0° for 3 seconds so IMU can settle
  // This creates a visible flat region for alignment
  Serial.println("# HOLDING_AT_ZERO");
  delay(3000);
  
  Serial.println("# SWEEP_START");
}

void logStep(int cycle, const char* dir, int pos) {
  Serial.print(millis());
  Serial.print(",");
  Serial.print(cycle);
  Serial.print(",");
  Serial.print(dir);
  Serial.print(",");
  Serial.println(pos);
}

void loop() {
  static int cycle = 0;

  if (cycle >= NUM_CYCLES) {
    // Hold at 0° at end — another alignment marker
    myServo.write(0);
    Serial.println("# TEST_COMPLETE");
    while (true);
  }

  // ── Forward 0° → 180° ─────────────────────
  for (int pos = 0; pos <= 180; pos += STEP_DEG) {
    myServo.write(pos);
    delay(SETTLE_MS);
    logStep(cycle, "FWD", pos);
    delay(STEP_DELAY_MS - SETTLE_MS);
  }

  Serial.println("# PAUSE_180");
  delay(PAUSE_MS);

  // ── Backward 180° → 0° ────────────────────
  for (int pos = 180; pos >= 0; pos -= STEP_DEG) {
    myServo.write(pos);
    delay(SETTLE_MS);
    logStep(cycle, "BWD", pos);
    delay(STEP_DELAY_MS - SETTLE_MS);
  }

  Serial.println("# PAUSE_0");
  delay(PAUSE_MS);

  cycle++;
}
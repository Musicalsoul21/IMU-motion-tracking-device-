#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>

#define SD_CS_PIN   PA4

// ── ⚠️ CHANGE THIS FOR EACH STM32 ─────────────
// STM32 #1 → FILE_PREFIX = "S1"  → creates S1001.CSV
// STM32 #2 → FILE_PREFIX = "S2"  → creates S2001.CSV
#define FILE_PREFIX "S1"
// ──────────────────────────────────────────────

Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x28);
File    logFile;
char    fileName[13];
uint32_t sampleCount = 0;
uint32_t flushCount  = 0;

unsigned long lastLogMs = 0;
const unsigned long LOG_INTERVAL_MS = 10;  // 100Hz

unsigned long lastBlinkMs = 0;
const unsigned long BLINK_INTERVAL_MS = 500;
bool ledState = LOW;

// ─────────────────────────────────────────────
void blinkForever(int n) {
  while (1) {
    for (int i = 0; i < n; i++) {
      digitalWrite(LED_BUILTIN, HIGH); delay(150);
      digitalWrite(LED_BUILTIN, LOW);  delay(150);
    }
    delay(1000);
  }
}

void blinkOK() {
  for (int i = 0; i < 6; i++) {
    digitalWrite(LED_BUILTIN, HIGH); delay(80);
    digitalWrite(LED_BUILTIN, LOW);  delay(80);
  }
}

// ─────────────────────────────────────────────
bool createLogFile() {
  char prefix[4];
  strncpy(prefix, FILE_PREFIX, sizeof(prefix));
  prefix[sizeof(prefix) - 1] = '\0';

  for (int i = 1; i <= 999; i++) {
    snprintf(fileName, sizeof(fileName), "%s%03d.CSV", prefix, i);
    if (!SD.exists(fileName)) {
      logFile = SD.open(fileName, FILE_WRITE);
      return (bool)logFile;
    }
  }
  return false;
}

void writeHeader() {
  logFile.println(
    "sample,time_ms,"
    "euler_x_deg,euler_y_deg,euler_z_deg,"
    "ax,ay,az,gx,gy,gz,"
    "qw,qx,qy,qz,"
    "calib_sys,calib_gyro,calib_accel,calib_mag"
  );
  logFile.flush();
}

// ─────────────────────────────────────────────
void updateBlink(unsigned long now) {
  if (now - lastBlinkMs >= BLINK_INTERVAL_MS) {
    lastBlinkMs = now;
    ledState = !ledState;
    digitalWrite(LED_BUILTIN, ledState);
  }
}

void logRow(unsigned long now) {
  imu::Vector<3>  eul  = bno.getVector(Adafruit_BNO055::VECTOR_EULER);
  imu::Vector<3>  acc  = bno.getVector(Adafruit_BNO055::VECTOR_ACCELEROMETER);
  imu::Vector<3>  gyr  = bno.getVector(Adafruit_BNO055::VECTOR_GYROSCOPE);
  imu::Quaternion quat = bno.getQuat();

  uint8_t sys, gyro, accel, mag;
  bno.getCalibration(&sys, &gyro, &accel, &mag);

  sampleCount++;

  logFile.print(sampleCount); logFile.print(",");
  logFile.print(now);         logFile.print(",");

  logFile.print(eul.x(), 4);  logFile.print(",");
  logFile.print(eul.y(), 4);  logFile.print(",");
  logFile.print(eul.z(), 4);  logFile.print(",");

  logFile.print(acc.x(), 4);  logFile.print(",");
  logFile.print(acc.y(), 4);  logFile.print(",");
  logFile.print(acc.z(), 4);  logFile.print(",");

  logFile.print(gyr.x(), 4);  logFile.print(",");
  logFile.print(gyr.y(), 4);  logFile.print(",");
  logFile.print(gyr.z(), 4);  logFile.print(",");

  logFile.print(quat.w(), 6); logFile.print(",");
  logFile.print(quat.x(), 6); logFile.print(",");
  logFile.print(quat.y(), 6); logFile.print(",");
  logFile.print(quat.z(), 6); logFile.print(",");

  logFile.print(sys);   logFile.print(",");
  logFile.print(gyro);  logFile.print(",");
  logFile.print(accel); logFile.print(",");
  logFile.println(mag);

  flushCount++;
  if (flushCount >= 10) {
    logFile.flush();
    flushCount = 0;
  }
}

// ─────────────────────────────────────────────
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  Wire.begin();
  delay(500);

  if (!bno.begin()) blinkForever(3);
  delay(1000);
  bno.setExtCrystalUse(true);

  SPI.begin();
  if (!SD.begin(SD_CS_PIN)) blinkForever(4);
  if (!createLogFile())    blinkForever(5);

  writeHeader();
  blinkOK();   // ready — starts logging immediately
}

// ─────────────────────────────────────────────
void loop() {
  unsigned long now = millis();

  updateBlink(now);

  if (now - lastLogMs >= LOG_INTERVAL_MS) {
    lastLogMs = now;
    logRow(now);
  }
}

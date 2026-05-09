#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>

#define SD_CS_PIN PA4

Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x28);
File logFile;
char fileName[13];

unsigned long lastLogMs = 0;
const unsigned long LOG_INTERVAL_MS = 10;  // 100Hz
uint32_t flushCount  = 0;
uint32_t sampleCount = 0;

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

bool createLogFile() {
  for (int i = 1; i <= 999; i++) {
    snprintf(fileName, sizeof(fileName), "VAL%03d.CSV", i);
    if (!SD.exists(fileName)) {
      logFile = SD.open(fileName, FILE_WRITE);
      return (bool)logFile;
    }
  }
  return false;
}

void writeHeader() {
  // time_ms is STM32 internal clock from power-on
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
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  Wire.begin();
  delay(500);

  if (!bno.begin())       blinkForever(3);  // 3 blinks = BNO055 error
  delay(1000);
  bno.setExtCrystalUse(true);

  SPI.begin();
  if (!SD.begin(SD_CS_PIN))   blinkForever(4);  // 4 = SD error
  if (!createLogFile())        blinkForever(5);  // 5 = file error

  writeHeader();
  blinkOK();  // 6 fast blinks = all good, logging starts NOW
}

// ─────────────────────────────────────────────
void loop() {
  unsigned long now = millis();

  if (now - lastLogMs >= LOG_INTERVAL_MS) {
    lastLogMs = now;

    imu::Vector<3>  eul  = bno.getVector(Adafruit_BNO055::VECTOR_EULER);
    imu::Vector<3>  acc  = bno.getVector(Adafruit_BNO055::VECTOR_ACCELEROMETER);
    imu::Vector<3>  gyr  = bno.getVector(Adafruit_BNO055::VECTOR_GYROSCOPE);
    imu::Quaternion quat = bno.getQuat();
    uint8_t sys, gyro, accel, mag;
    bno.getCalibration(&sys, &gyro, &accel, &mag);

    sampleCount++;

    logFile.print(sampleCount);      logFile.print(",");
    logFile.print(now);              logFile.print(",");

    // Euler angles — all three axes logged
    // We'll figure out which axis in Python
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
}
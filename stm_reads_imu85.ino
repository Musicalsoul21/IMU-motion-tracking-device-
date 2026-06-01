#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>

#define SD_CS_PIN PA4

Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x28);
File logFile;

unsigned long lastLogMs = 0;
const unsigned long LOG_INTERVAL_MS = 10;   // 100 Hz
uint32_t flushCounter = 0;
char fileName[13]; // 8.3 filename format, e.g. LOG001.CSV

void blinkForever(int count, int onMs = 150, int offMs = 150, int gapMs = 1000) {
  while (1) {
    for (int i = 0; i < count; i++) {
      digitalWrite(LED_BUILTIN, HIGH);
      delay(onMs);
      digitalWrite(LED_BUILTIN, LOW);
      delay(offMs);
    }
    delay(gapMs);
  }
}

bool createNewLogFile() {
  for (int i = 1; i <= 999; i++) {
    snprintf(fileName, sizeof(fileName), "LOG%03d.CSV", i);
    if (!SD.exists(fileName)) {
      logFile = SD.open(fileName, FILE_WRITE);
      return logFile;
    }
  }
  return false;
}

void writeHeader() {
  logFile.println("session,file,time_ms,ax_mps2,ay_mps2,az_mps2,gx_rps,gy_rps,gz_rps,mx_uT,my_uT,mz_uT,roll_deg,pitch_deg,yaw_deg,qw,qx,qy,qz");
  logFile.flush();
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  Wire.begin();
  delay(500);

  if (!bno.begin()) {
    blinkForever(3);   // BNO055 not found
  }

  delay(1000);
  bno.setExtCrystalUse(true);

  SPI.begin();

  if (!SD.begin(SD_CS_PIN)) {
    blinkForever(4);   // SD init failed
  }

  if (!createNewLogFile()) {
    blinkForever(5);   // file creation failed
  }

  writeHeader();

  for (int i = 0; i < 6; i++) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(80);
    digitalWrite(LED_BUILTIN, LOW);
    delay(80);
  }
}

void loop() {
  unsigned long now = millis();

  if (now - lastLogMs >= LOG_INTERVAL_MS) {
    imu::Vector<3> acc = bno.getVector(Adafruit_BNO055::VECTOR_ACCELEROMETER);
    imu::Vector<3> gyr = bno.getVector(Adafruit_BNO055::VECTOR_GYROSCOPE);
    imu::Vector<3> mag = bno.getVector(Adafruit_BNO055::VECTOR_MAGNETOMETER);
    imu::Vector<3> eul = bno.getVector(Adafruit_BNO055::VECTOR_EULER);
    imu::Quaternion quat = bno.getQuat();

    logFile.print(fileName);
    logFile.print(",");
    logFile.print(fileName);
    logFile.print(",");
    logFile.print(now);
    logFile.print(",");

    logFile.print(acc.x(), 4); logFile.print(",");
    logFile.print(acc.y(), 4); logFile.print(",");
    logFile.print(acc.z(), 4); logFile.print(",");

    logFile.print(gyr.x(), 4); logFile.print(",");
    logFile.print(gyr.y(), 4); logFile.print(",");
    logFile.print(gyr.z(), 4); logFile.print(",");

    logFile.print(mag.x(), 4); logFile.print(",");
    logFile.print(mag.y(), 4); logFile.print(",");
    logFile.print(mag.z(), 4); logFile.print(",");

    logFile.print(eul.x(), 4); logFile.print(",");
    logFile.print(eul.y(), 4); logFile.print(",");
    logFile.print(eul.z(), 4); logFile.print(",");

    logFile.print(quat.w(), 6); logFile.print(",");
    logFile.print(quat.x(), 6); logFile.print(",");
    logFile.print(quat.y(), 6); logFile.print(",");
    logFile.println(quat.z(), 6);

    flushCounter++;
    if (flushCounter >= 10) {
      logFile.flush();
      flushCounter = 0;
    }

    digitalWrite(LED_BUILTIN, HIGH);
    delay(20);
    digitalWrite(LED_BUILTIN, LOW);

    lastLogMs = now;
  }
}

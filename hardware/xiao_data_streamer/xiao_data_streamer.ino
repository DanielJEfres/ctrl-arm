#include <Wire.h>
#include "LSM6DS3.h"


LSM6DS3 imu(I2C_MODE, 0x6A);  // 0x6b if ts doesnt work


const float ALPHA = 0.12f;
const float DEADZONE = 0.01f;


const int SAMPLE_RATE_HZ = 200;
const int SAMPLE_PERIOD_MS = 1000 ;
const int EMG_PINS[] = {A0, A1};
const int NUM_EMG_SENSORS = 2;

unsigned long lastSampleTime = 0;
unsigned long startTime = 0;

// imu smoothened
float accelXSm = 0, accelYSm = 0, accelZSm = 0;
float gyroXSm = 0, gyroYSm = 0, gyroZSm = 0;
bool firstIMURead = true;

void setup() {
  Serial.begin(115200);
  delay(400);
  
  Serial.println("# Starting XIAO");

  for (int i = 0; i < NUM_EMG_SENSORS; i++) {
    pinMode(EMG_PINS[i], INPUT);
    int testRead = analogRead(EMG_PINS[i]);
    Serial.print("# EMG");
    Serial.print(i + 1);
    Serial.print(" on pin A");
    Serial.print(i);
    Serial.print(" reads: ");
    Serial.println(testRead);
  }
  
  Wire.begin();

  if (imu.begin() != 0) {
    Serial.println("# IMU init failed.");
  } else {
    Serial.println("# IMU working woohooo");
  }
  startTime = millis();
}

void loop() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastSampleTime >= SAMPLE_PERIOD_MS) {
    lastSampleTime = currentTime;
    
    // read emg sensors for data
    int emgValues[NUM_EMG_SENSORS];
    for (int i = 0; i < NUM_EMG_SENSORS; i++) {
      emgValues[i] = analogRead(EMG_PINS[i]);
      delayMicroseconds(100); //delay for ml stability
    }

    float accelX = imu.readFloatAccelX();
    float accelY = imu.readFloatAccelY();
    float accelZ = imu.readFloatAccelZ();
    float gyroX = imu.readFloatGyroX();
    float gyroY = imu.readFloatGyroY();
    float gyroZ = imu.readFloatGyroZ();
    
    if (firstIMURead) {
      accelXSm = accelX; accelYSm = accelY; accelZSm = accelZ;
      gyroXSm = gyroX; gyroYSm = gyroY; gyroZSm = gyroZ;
      firstIMURead = false;
    } else {
      accelXSm = ALPHA * accelX + (1.0f - ALPHA) * accelXSm;
      accelYSm = ALPHA * accelY + (1.0f - ALPHA) * accelYSm;
      accelZSm = ALPHA * accelZ + (1.0f - ALPHA) * accelZSm;
      gyroXSm = ALPHA * gyroX + (1.0f - ALPHA) * gyroXSm;
      gyroYSm = ALPHA * gyroY + (1.0f - ALPHA) * gyroYSm;
      gyroZSm = ALPHA * gyroZ + (1.0f - ALPHA) * gyroZSm;
    }
    
    if (fabsf(accelXSm) < DEADZONE) accelXSm = 0.0f;
    if (fabsf(accelYSm) < DEADZONE) accelYSm = 0.0f;
    if (fabsf(gyroXSm) < 1.0f) gyroXSm = 0.0f;
    if (fabsf(gyroYSm) < 1.0f) gyroYSm = 0.0f;
    if (fabsf(gyroZSm) < 1.0f) gyroZSm = 0.0f;
    
    // time stamp
    unsigned long timestamp = currentTime - startTime;
    
    // csv 
    Serial.print(timestamp);
    Serial.print(",");
    
    for (int i = 0; i < NUM_EMG_SENSORS; i++) {
      Serial.print(emgValues[i]);
      Serial.print(",");
    }
    
    Serial.print(accelXSm, 3);
    Serial.print(",");
    Serial.print(accelYSm, 3);
    Serial.print(",");
    Serial.print(accelZSm, 3);
    Serial.print(",");
    Serial.print(gyroXSm, 3);
    Serial.print(",");
    Serial.print(gyroYSm, 3);
    Serial.print(",");
    Serial.print(gyroZSm, 3);
    Serial.println();
  }
}

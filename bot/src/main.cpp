#include <Arduino.h>
#define SONAR_PIN 3

long duration;
float distance;

void setup() {
  Serial.begin(9600);
}

void loop() {
  // Send trigger pulse
  pinMode(SONAR_PIN, OUTPUT);
  digitalWrite(SONAR_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(SONAR_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(SONAR_PIN, LOW);

  // Listen for echo
  pinMode(SONAR_PIN, INPUT);
  duration = pulseIn(SONAR_PIN, HIGH, 30000); // 30 ms timeout

  if (duration == 0) {
    Serial.println("Out of range");
  } else {
    float distance = duration * 0.0343 / 2;
    Serial.println(distance);
  }

  delay(1000);
}


#include <Arduino.h>
#include <Servo.h>

Servo servo;

const int servo_pin = 9;
int incomingByte = 0;

void setup() {
  Serial.begin(9600);
  Serial.println("Start program"); 

  servo.attach(servo_pin);
  servo.write(0);

  if (!servo.attached()) {
    Serial.println("Servo not attached!");
  }
}

void loop() {

  if (Serial.available() > 0) {
    // read the incoming byte:
    incomingByte = Serial.read();

    Serial.println("I received:");

    if (incomingByte == '1') {
      servo.write(114);
    }
  }
  delay(20);
} 



#include <Arduino.h>
#include <Servo.h>

Servo servo;

const int servo_pin = 9;
int incomingByte = 0;

void setup() {
  Serial.begin(9600);
  Serial.println("Start program"); 

}

void loop() {

  if (Serial.available() > 0) {
    // read the incoming byte:
    incomingByte = Serial.read();

    Serial.println("I received:");

    if (incomingByte == '1') {
      servo.attach(servo_pin);
      delay(100);
      servo.write(114);
      delay(1000);
      servo.write(150);
      delay(500);
      servo.detach();
    }
  }
  delay(20);
} 



#include <Arduino.h>

uint8_t mReadStatus = 1;    // 0: Open, 1: Detect

void setup() {
  // initialize the serial communication:
  Serial.begin(115200);
  pinMode(2, INPUT); // Setup for leads off detection LO +
  pinMode(3, INPUT); // Setup for leads off detection LO -

}

void loop() {
  if((digitalRead(2) == 1)||(digitalRead(3) == 1))
  {
    if(mReadStatus)
    {
       mReadStatus = 0;
       Serial.println("Can't detect read !");
    }
  }
  else
  {
    mReadStatus = 1;
    // send the value of analog input 0:
      Serial.print("$");
      Serial.print(analogRead(A0));
      Serial.print(";");
  }
  //Wait for a bit to keep serial data from saturating
  delay(1);
}

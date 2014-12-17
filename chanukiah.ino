// Reminder: LED max analog is 255

/*
* SERIAL COMMANDS
* Send commands as ASCII within greater and less than symbols. Ie: <8>.
* 1-8: light n candles (including shamash, if off)
* 9: kill all lights
* 10: light shamash only
* 13: error
* 14: heartbeat
* 15: reset
*/
 
// Define shamash RGB LED
const int shamash_r = 10;
const int shamash_g = 11;
const int shamash_b = 9;
const int error_led = 13;

// Define pins for other candle LEDs
int candles[] = {2, 3, 4, 5, 6, 7, 8, 12};

// Keep track of current serial command / night of chag
int serial_command = 0;

// Are the candles lit?
int candles_lit = 0;

// Serial variables
char inData[10];
int index;
boolean started = false;
boolean ended = false;
char output_buffer[50];

void setup() {
  // Set up pin modes
  pinMode(shamash_r, OUTPUT);
  pinMode(shamash_g, OUTPUT);
  pinMode(shamash_b, OUTPUT);
  pinMode(error_led, OUTPUT);
  pinMode(candles[0], OUTPUT);
  pinMode(candles[1], OUTPUT);
  pinMode(candles[2], OUTPUT);
  pinMode(candles[3], OUTPUT);
  pinMode(candles[4], OUTPUT);
  pinMode(candles[5], OUTPUT);
  pinMode(candles[6], OUTPUT);
  pinMode(candles[7], OUTPUT);
  
  // Open the serial port
  Serial.begin(9600);
}

void loop() {  
  readSerial();
  
  if (serial_command != 9 && serial_command != 15 && serial_command != 10 && serial_command != 13 && serial_command != 0 && serial_command != 14 && serial_command > 0 && serial_command < 16) {
    lightCandles(serial_command);
    serial_command = 0;
  } else if (serial_command == 9) {
    extinguishCandles();
    serial_command = 0;
  } else if (serial_command == 13) {
    inError(1);
    serial_command = 0;
  } else if (serial_command == 10) {
    lightShamash();
    serial_command = 0;
  } else if (serial_command == 15) {
    reset();
    serial_command = 0;
  }
}

void reset() {
  candles_lit = 0;
  serial_command = 0;
  inError(0);
  index = 0;
  started = false;
  ended = false;
  extinguishCandles();
}

void lightCandles(int night) {
  if (candles_lit == 1) {
    extinguishCandles();
  }
  lightShamash();
  //Serial.print("<MSG:Lighting ");
  //Serial.print(night);
  //Serial.println(" candles.>");
  for(int i = 0; i < night; i++) {
    digitalWrite(candles[i], HIGH);
    //delay(1000);
  }
  candles_lit = 1;
  serial_command = 0;
}

void extinguishCandles() {
  //Serial.println("<MSG:Extinguishing candles.>");
  for (int i = 8; i >= 0; i--) {
    digitalWrite(candles[i], LOW);
    //delay(1000);
  }
  analogWrite(shamash_r, 0);
  analogWrite(shamash_g, 0);
  analogWrite(shamash_b, 0);
  candles_lit = 0;
  serial_command = 0;
}

void lightShamash() {
  //Serial.println("<MSG:Lighting smahash.>");
  analogWrite(shamash_r, 255);
  analogWrite(shamash_g, 255);
  analogWrite(shamash_b, 255);
}

void inError(int value) {
  if (value==0) {
    digitalWrite(error_led, LOW);
  } else {
    digitalWrite(error_led, HIGH);
  }
}

// Adapted from PaulS's solution on http://forum.arduino.cc/index.php/topic,39609.0.html
// We need a complex process to read serial data because python transmits over serial in ASCII.
void readSerial()
{
  while((Serial.available() > 0) && (ended == false))
  {
      char aChar = Serial.read();
      
      if(aChar == '<')
      {
          started = true;
          index = 0;
          inData[index] = '\0';
      }
      else if(aChar == '>')
      {
          ended = true;
      }
      else if(started)
      {
          inData[index] = aChar;
          index++;
          inData[index] = '\0';
      }
  }

  if(started && ended)
  {
      // Convert the string to an integer
      serial_command = atoi(inData);
      
      Serial.print("<ACK:");
      Serial.print(serial_command);
      Serial.println(">");

      // Get ready for the next time
      started = false;
      ended = false;

      index = 0;
      inData[index] = '\0';
  }
}

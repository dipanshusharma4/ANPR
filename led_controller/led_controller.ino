// ANPR Boom Barrier Arduino Code - Prototype (LEDs Only)
const int GREEN_LED = 8;
const int RED_LED = 9;

String command = "";
bool barrierOpen = false;

void setup() {
  Serial.begin(9600);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  
  // Initial state - barrier closed
  digitalWrite(RED_LED, HIGH);
  digitalWrite(GREEN_LED, LOW);
  
  Serial.println("READY"); // Signal to Python that Arduino is ready
}

void loop() {
  if (Serial.available() > 0) {
    command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "OPEN") {
      openBarrier();
      Serial.println("ACK:OPEN");
    } 
    else if (command == "CLOSE") {
      closeBarrier();
      Serial.println("ACK:CLOSE");
    }
    else if (command == "STATUS") {
      if (barrierOpen) {
        Serial.println("STATUS:OPEN");
      } else {
        Serial.println("STATUS:CLOSED");
      }
    }
    else {
      Serial.println("ERR:UNKNOWN_COMMAND");
    }
  }
}

void openBarrier() {
  digitalWrite(RED_LED, LOW);
  digitalWrite(GREEN_LED, HIGH);
  barrierOpen = true;
  
  // Auto-close after 5 seconds (adjustable)
  delay(5000);
  closeBarrier();
}

void closeBarrier() {
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, HIGH);
  barrierOpen = false;
}

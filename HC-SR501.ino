// Constants for hardware pins
const int sensorPin = 8;        // PIR sensor output pin

// Debounce configuration (in milliseconds)
const long debounceDelay = 50;  // Time to confirm stable sensor state

// State tracking variables
int pirState = LOW;             // Current motion detection state
int lastSensorValue = LOW;      // Previous sensor reading
int currentSensorState = LOW;   // Debounced sensor state
unsigned long lastDebounceTime = 0; // Timestamp for debounce logic

void setup() {
  // Initialize sensor pin
  pinMode(sensorPin, INPUT);
  
  // Initialize serial communication (9600 baud matches Linux default)
  Serial.begin(9600);
  
  // Allow sensor calibration time (60 seconds recommended)
  Serial.println("Calibrating PIR sensor...");
  delay(60000);  // 60-second calibration period
  Serial.println("Sensor ready!");
}

void loop() {
  // Read sensor value
  int sensorValue = digitalRead(sensorPin);

  // Debounce logic using millis() to prevent false triggers
  if (sensorValue != lastSensorValue) {
    lastDebounceTime = millis();  // Reset debounce timer on change
  }

  // Update current state only if stable for debounce period
  if ((millis() - lastDebounceTime) > debounceDelay) {
    currentSensorState = sensorValue;
  }

  // Update last sensor value for next iteration
  lastSensorValue = sensorValue;

  // Handle motion detection state changes
  if (currentSensorState == HIGH) {
    // Only trigger action on state change
    if (pirState == LOW) {
      Serial.println("Motion detected!");
      pirState = HIGH;
    }
  } 
  else {
    // Only trigger action on state change
    if (pirState == HIGH) {
      Serial.println("Motion ended!");
      pirState = LOW;
    }
  }
}

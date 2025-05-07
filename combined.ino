// === PIR Motion Detection Configuration ===
const int sensorPin = 8;             // PIR sensor output pin
const long debounceDelay = 50;       // Debounce delay (ms)

// PIR state tracking
int pirState = LOW;                  // Current motion state
int lastSensorValue = LOW;           // Previous sensor reading
int currentSensorState = LOW;        // Debounced state
unsigned long lastDebounceTime = 0;  // Last state change timestamp

// === Setup: Initialization ===
void setup() {
  pinMode(sensorPin, INPUT);         // Initialize PIR sensor pin
  Serial.begin(115200);              // Start serial at 115200 baud

  // Allow PIR sensor calibration time
  Serial.println("Calibrating PIR sensor...");
  delay(60000);                      // 60-second warm-up
  Serial.println("Sensor ready!");
}

// === Main Loop: Motion Detection + Temperature Query ===
void loop() {
  // --- Motion Detection Logic ---
  int sensorValue = digitalRead(sensorPin);

  // Debounce: Only update state if stable for debounceDelay
  if (sensorValue != lastSensorValue) {
    lastDebounceTime = millis();     // Reset debounce timer
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    currentSensorState = sensorValue;
  }

  lastSensorValue = sensorValue;

  // Report motion state changes
  if (currentSensorState == HIGH && pirState == LOW) {
    Serial.println("Motion detected!");
    pirState = HIGH;
  } else if (currentSensorState == LOW && pirState == HIGH) {
    Serial.println("Motion ended!");
    pirState = LOW;
  }

  // --- Temperature Query Handling ---
  if (Serial.available() > 0) {
    char query = Serial.read();

    if (query == 'T') {
      // Read analog temperature sensor (A5)
      unsigned int ADC_Value = analogRead(A5);
      
      // Convert ADC to temperature (adjust formula if needed)
      float temperature = ((double)ADC_Value * 340.0 / 614.4 - 70.0);
      
      // Output temperature value
      Serial.println(temperature);
    }
  }
}

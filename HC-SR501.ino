// === PIR Motion Sensor Project ===
// This sketch reads from a PIR motion sensor,
// debounces the signal, and prints messages when motion starts or stops.

// === Pin Setup ===
const int PIR_PIN = 8; // PIR sensor connected to digital pin 8

// === Debounce Timing ===
// We use a short delay to ignore quick flickers in sensor signal
const unsigned long DEBOUNCE_DELAY_MS = 50;

// === Variables to track state ===
int currentPirReading = LOW;     // What we just read from the sensor
int lastPirReading = LOW;        // Previous reading to detect changes
unsigned long lastDebounceTime;  // When the sensor last changed state
bool motionDetected = false;     // Final debounced state: is there motion?

void setup() {
  // Start serial communication so we can send messages to the computer
  Serial.begin(9600);

  // Tell Arduino that the PIR pin is an input
  pinMode(PIR_PIN, INPUT);

  // Let the PIR sensor warm up - it needs about 60 seconds to calibrate
  Serial.println("Warming up PIR sensor...");
  delay(60000); // Wait for one minute
  Serial.println("Sensor ready! Ready to detect motion.");
}

void loop() {
  // Read the current value from the PIR sensor
  currentPirReading = digitalRead(PIR_PIN);

  // If the new reading is different from the last one, reset the debounce timer
  if (currentPirReading != lastPirReading) {
    lastDebounceTime = millis();
  }

  // Only update the motion state if the reading has been stable for longer than the debounce time
  if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY_MS) {
    // If the motion state has actually changed
    if (currentPirReading != motionDetected) {
      motionDetected = currentPirReading;

      // Print out a message based on whether motion started or stopped
      if (motionDetected) {
        Serial.println("Motion detected!");
      } else {
        Serial.println("Motion ended.");
      }
    }
  }

  // Save this reading for next loop iteration
  lastPirReading = currentPirReading;
}

/*
 * === PIR Motion Sensor Project ===
 * 
 * This sketch reads from a PIR motion sensor,
 * debounces the signal, and prints messages when motion starts or stops.
 */

// -----------------------------
// Configuration Section
// -----------------------------

// Hardware configuration
constexpr int PIR_PIN = 8; // PIR sensor connected to digital pin 8

// Timing settings
constexpr unsigned long DEBOUNCE_DELAY_MS = 50; // Time to wait before accepting a stable state
constexpr unsigned long SENSOR_WARMUP_TIME_MS = 60000; // Time for PIR to calibrate

// Serial communication
constexpr long BAUD_RATE = 9600;

// -----------------------------
// Global State Variables
// -----------------------------
int currentReading = LOW;
int lastReading = LOW;
unsigned long lastDebounceTime = 0;
bool motionDetected = false;

// -----------------------------
// Function Declarations
// -----------------------------
void setupSensor();
void updateMotionState();
void printMotionStatusChange(bool motionActive);

// -----------------------------
// Setup: Runs once at startup
// -----------------------------
void setup() {
    // Initialize serial communication
    Serial.begin(BAUD_RATE);

    // Configure hardware
    setupSensor();

    // Allow time for PIR to stabilize
    Serial.println("Warming up PIR sensor...");
    delay(SENSOR_WARMUP_TIME_MS);
    Serial.println("Sensor ready! Ready to detect motion.");
}

// -----------------------------
// Loop: Main program loop
// -----------------------------
void loop() {
    // Read current value from PIR sensor
    currentReading = digitalRead(PIR_PIN);

    // Update motion detection logic
    updateMotionState();
}

// -----------------------------
// Initialize sensor pin
// -----------------------------
void setupSensor() {
    pinMode(PIR_PIN, INPUT);
}

// -----------------------------
// Update motion detection state with debounce
// -----------------------------
void updateMotionState() {
    if (currentReading != lastReading) {
        // Reset debounce timer on change
        lastDebounceTime = millis();
    }

    // Only consider the change valid after debounce period
    if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY_MS) {
        if (currentReading != motionDetected) {
            motionDetected = currentReading;
            printMotionStatusChange(motionDetected);
        }
    }

    // Save reading for next iteration
    lastReading = currentReading;
}

// -----------------------------
// Print message based on motion state
// -----------------------------
void printMotionStatusChange(bool motionActive) {
    if (motionActive) {
        Serial.println("Motion detected!");
    } else {
        Serial.println("Motion ended.");
    }
}

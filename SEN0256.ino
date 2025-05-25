Rewrite the following code to follow best practices for c++

// === Temperature Monitor Project ===
// This program waits for you to send the letter 'R' over serial.
// When it gets that command, it reads the analog temperature sensor on pin A5,
// converts the value into degrees Celsius, and prints it to the Serial Monitor.

// --- Configuration Section ---
// These values are used to convert raw sensor data into actual temperature
const int TEMP_SENSOR_PIN = A5;     // Sensor connected to analog pin A5
const float V_REF = 340;            // Scaling factor (adjust if needed: try 340 or 450)
const float V_DENOM = 614.4;        // From ADC range and voltage reference
const float CAL_OFFSET = -70;       // Calibration offset from sensor specs

// --- Setup: Runs Once at Start ---
void setup() {
  // Start serial communication so we can talk to the computer
  Serial.begin(115200);

  // Give everything a second to get ready
  delay(1000);

  // Friendly startup message
  // Serial.println("Temperature Monitor is Running!");
  // Serial.println("Send the letter 'R' to get a temperature reading.");
}

// --- Loop: Waits for Commands and Responds ---
void loop() {
  // Check if something was sent through the serial port
  if (Serial.available() > 0) {
    char incomingChar = Serial.read(); // Read one character

    // If it's an 'R', take a temperature reading
    if (incomingChar == 'R') {
      // Read the raw analog value from the sensor
      int sensorValue = analogRead(TEMP_SENSOR_PIN);

      // Convert the raw number into real temperature using a formula:
      // ((ADC * scaling factor / denominator) + calibration offset)
      float temperature = ((float)sensorValue * V_REF / V_DENOM) + CAL_OFFSET;

      // Print the result so we can see it in the Serial Monitor
      Serial.print(temperature, 1); // Show one decimal place
    }
  }
}

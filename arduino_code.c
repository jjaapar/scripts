// === Temperature Monitoring System ===
// Waits for a 'T' command over serial, reads temperature from analog pin A5,
// converts it to degrees Celsius, prints the value, and checks for overheating.

// === Setup: Initialize Serial Communication ===
void setup() {
  // Start serial communication at 115200 baud rate
  Serial.begin(115200);

  // Wait a moment for things to settle
  delay(1000);
  Serial.println("🌡️ Temperature Monitor Started!");
  Serial.println("Send 'R' to request temperature reading.");
}

// === Main Loop: Listen for commands and respond ===
void loop() {
  // Only do something if there's data in the serial buffer
  if (Serial.available() > 0) {
    char incomingChar = Serial.read(); // Read one character

    // If the character is 'T', take a temperature reading
    if (incomingChar == 'R') {
      // Read raw analog value from the sensor on pin A5
      int sensorValue = analogRead(A5);

      // Convert the raw value to temperature in degrees Celsius
      // Formula: ((ADC * 340 / 614.4) - 70)
      // Adjust "340" to "450" if needed based on your sensor calibration
      float temperature = ((float)sensorValue * 340 / 614.4 - 70);

      // Print the temperature to the serial monitor
      Serial.print(temperature);
    }
  }
}

// Initialize the serial communication
void setup() {
  Serial.begin(115200); // Set baud rate for serial communication
}

// Function to check for high temperature and alert
void checkTemperatureAlert(float temperature) {
  if (temperature > 100) {
    Serial.println("Warning: Temperature exceeded 100â„ƒ!");
  }
}

void loop() {
  // Check if there is data available in the serial buffer
  if (Serial.available() > 0) {
    char query = Serial.read(); // Read incoming query
    if (query == 'T') { // If query is 'T', return temperature data
      unsigned int ADC_Value = analogRead(A5); // Read temperature sensor value
      float temperature = ((double)ADC_Value * 340 / 614.4 - 70); 
      // If the measured temperature is incorrect, adjust 340 to 450
      
      // Serial.print("Temperature: ");
      Serial.print(temperature);
      // Serial.println(" C");
      
      checkTemperatureAlert(temperature); // Check for high temperature alert
    }
  }
}

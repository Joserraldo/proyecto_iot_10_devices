/*
  D2 - Meteo patio/cubierta - Campus UNAB
  Wokwi ESP32: DHT22 + LDR (photoresistor) + MQTT
  Publica cada 30s en campus/ems/D2
  Formato: {"temperature":XX.X,"humidity":XX.X,"lux":XX.X}
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// --- Configuracion WiFi (Wokwi-GUEST para simulador) ---
const char* ssid     = "Wokwi-GUEST";
const char* password = "";

// --- Configuracion MQTT ---
const char* mqtt_server  = "test.mosquitto.org";
const int   mqtt_port    = 1883;
const char* mqtt_topic   = "campus/ems/D2";
const char* client_id    = "campus-ems-02";

// --- Sensores ---
#define DHTPIN  4
#define DHTTYPE DHT22
#define LDR_PIN 34        // AO del photoresistor (ADC en GPIO34)
#define LDR_GAMMA 0.7
#define LDR_RL10  50.0
DHT   dht(DHTPIN, DHTTYPE);

// --- Clientes ---
WiFiClient   espClient;
PubSubClient mqttClient(espClient);

// --- LED estado ---
#define LED_PIN 2

void connectWiFi() {
  Serial.print("Conectando WiFi");
  WiFi.begin(ssid, password);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi OK: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nWiFi FALLO — continuando sin red");
  }
}

void connectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Conectando MQTT...");
    if (mqttClient.connect(client_id)) {
      Serial.println("OK");
      digitalWrite(LED_PIN, HIGH);
    } else {
      Serial.print("Fallo rc=");
      Serial.print(mqttClient.state());
      Serial.println(" reintentando en 5s");
      delay(5000);
    }
  }
}

float readLux() {
  int analogValue = analogRead(LDR_PIN);
  float voltage   = analogValue / 4095.0 * 3.3;
  if (voltage <= 0.001) voltage = 0.001;
  if (voltage >= 3.299) voltage = 3.299;
  // LDR en serie con 10K, AO en el divisor
  float resistance = 10000.0 * (3.3 - voltage) / voltage;
  if (!isfinite(resistance) || resistance <= 0) return 0.0;
  float lux = pow(LDR_RL10 * 1e3 * pow(10.0, LDR_GAMMA) / resistance, 1.0 / LDR_GAMMA);
  if (!isfinite(lux)) return 0.0;
  return lux;
}

void publishData(float temp, float hum, float lux) {
  char payload[128];
  snprintf(payload, sizeof(payload),
           "{\"temperature\":%.1f,\"humidity\":%.1f,\"lux\":%.1f,\"source\":\"wokwi-d2\"}",
           temp, hum, lux);

  bool ok = mqttClient.publish(mqtt_topic, payload);
  if (ok) {
    Serial.print("[D2] Publicado en ");
    Serial.print(mqtt_topic);
    Serial.print(": ");
    Serial.println(payload);
  } else {
    Serial.println("[D2] Error publicando MQTT");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  dht.begin();

  connectWiFi();
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setKeepAlive(60);
  connectMQTT();

  Serial.println("[D2] Setup completo");
}

void loop() {
  // Mantener conexion MQTT
  if (!mqttClient.connected()) {
    digitalWrite(LED_PIN, LOW);
    connectMQTT();
  }
  mqttClient.loop();

  // Lectura sensores
  float h    = dht.readHumidity();
  float t    = dht.readTemperature();
  float lux  = readLux();

  if (isnan(h) || isnan(t)) {
    Serial.println("[D2] Error leyendo DHT22");
  } else {
    publishData(t, h, lux);
  }

  // Intervalo 30 segundos
  delay(30000);
}
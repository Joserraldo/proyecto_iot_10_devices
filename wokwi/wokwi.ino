/*
  D2 - Meteo patio/cubierta - Campus UNAB
  Wokwi ESP32: DHT22 + LDR + LED + MQTT verbose logging
  Publica cada 30s en campus/ems/D2
  Formato: {"temperature":XX.X,"humidity":XX.X,"lux":XX.X}

  EVIDENCIAS: cada etapa del init y loop imprime en Serial Monitor
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
#define LDR_PIN 34
#define LED_PIN 2

DHT dht(DHTPIN, DHTTYPE);

WiFiClient   espClient;
PubSubClient mqttClient(espClient);

// --- Contadores para logs ---
unsigned long loopCount = 0;

void printDivider() {
  Serial.println("========================================");
}

// ============ WIFI ============
void connectWiFi() {
  Serial.println("[WIFI] Iniciando conexion...");
  Serial.print("[WIFI] SSID: ");
  Serial.println(ssid);
  Serial.print("[WIFI] Password: ");
  Serial.println(strlen(password) > 0 ? password : "(vacio - Wokwi-GUEST)");
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  Serial.print("[WIFI] Intentando conectar");
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    printDivider();
    Serial.println("[WIFI] ✓ CONEXION EXITOSA");
    Serial.print("[WIFI] IP local: ");
    Serial.println(WiFi.localIP());
    Serial.print("[WIFI] Gateway: ");
    Serial.println(WiFi.gatewayIP());
    Serial.print("[WIFI] RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    printDivider();
  } else {
    Serial.println();
    Serial.println("[WIFI] ✗ FALLO - continuando sin red");
  }
}

// ============ MQTT ============
void connectMQTT() {
  Serial.println("[MQTT] Iniciando conexion a broker...");
  Serial.print("[MQTT] Server: ");
  Serial.println(mqtt_server);
  Serial.print("[MQTT] Puerto: ");
  Serial.println(mqtt_port);
  Serial.print("[MQTT] Topic: ");
  Serial.println(mqtt_topic);
  Serial.print("[MQTT] Client ID: ");
  Serial.println(client_id);
  
  int attempts = 0;
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Intento ");
    Serial.print(++attempts);
    Serial.print("... ");
    
    if (mqttClient.connect(client_id)) {
      Serial.println("OK");
      digitalWrite(LED_PIN, HIGH);
      printDivider();
      Serial.println("[MQTT] ✓ CONEXION EXITOSA AL BROKER");
      Serial.print("[MQTT] Estado: ");
      Serial.println(mqttClient.state());
      printDivider();
    } else {
      Serial.print("FALLO rc=");
      Serial.print(mqttClient.state());
      Serial.print(" (");
      switch (mqttClient.state()) {
        case -4: Serial.print("CONNECTION_TIMEOUT"); break;
        case -3: Serial.print("CONNECTION_LOST"); break;
        case -2: Serial.print("CONNECT_FAILED"); break;
        case -1: Serial.print("DISCONNECTED"); break;
        case 0:  Serial.print("CONNECTED"); break;
        default: Serial.print("UNKNOWN"); break;
      }
      Serial.println(")");
      Serial.println("[MQTT] Reintentando en 5s...");
      delay(5000);
    }
  }
}

// ============ LECTURA SENSORES ============
float readLux() {
  int analogValue = analogRead(LDR_PIN);
  float voltage   = analogValue / 4095.0 * 3.3;
  
  Serial.print("[LDR] Raw ADC: ");
  Serial.print(analogValue);
  Serial.print(" | Voltage: ");
  Serial.print(voltage, 3);
  Serial.print("V | ");
  
  if (voltage <= 0.001) voltage = 0.001;
  if (voltage >= 3.299) voltage = 3.299;
  
  float resistance = 10000.0 * (3.3 - voltage) / voltage;
  if (!isfinite(resistance) || resistance <= 0) {
    Serial.println("LDR error - retornando 0");
    return 0.0;
  }
  
  float lux = pow(LDR_RL10 * 1e3 * pow(10.0, LDR_GAMMA) / resistance, 1.0 / LDR_GAMMA);
  if (!isfinite(lux)) {
    Serial.println("LUX calculo error - retornando 0");
    return 0.0;
  }
  
  Serial.print("R=");
  Serial.print(resistance, 1);
  Serial.print(" ohm | Lux: ");
  Serial.println(lux, 1);
  
  return lux;
}

void readDHT(float& temp, float& hum) {
  hum = dht.readHumidity();
  temp = dht.readTemperature();
  
  Serial.print("[DHT22] Temperatura: ");
  if (isnan(temp)) {
    Serial.println("ERROR");
  } else {
    Serial.print(temp, 1);
    Serial.println(" C");
  }
  
  Serial.print("[DHT22] Humedad: ");
  if (isnan(hum)) {
    Serial.println("ERROR");
  } else {
    Serial.print(hum, 1);
    Serial.println(" %");
  }
}

// ============ PUBLICAR ============
void publishData(float temp, float hum, float lux) {
  char payload[128];
  snprintf(payload, sizeof(payload),
           "{\"temperature\":%.1f,\"humidity\":%.1f,\"lux\":%.1f,\"source\":\"wokwi-d2\"}",
           temp, hum, lux);

  Serial.print("[PUB] Payload: ");
  Serial.println(payload);
  
  bool ok = mqttClient.publish(mqtt_topic, payload);
  if (ok) {
    Serial.println("[PUB] ✓ Mensaje publicado exitosamente");
  } else {
    Serial.println("[PUB] ✗ ERROR - no se pudo publicar");
  }
}

// ============ SETUP ============
void setup() {
  Serial.begin(115200);
  delay(500);
  
  printDivider();
  Serial.println("[SETUP] ===== INICIANDO ESP32 D2 =====");
  Serial.println("[SETUP] Campus UNAB - Wokwi ESP32 Simulator");
  printDivider();
  
  // LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Serial.println("[SETUP] LED estado: OFF (esperando conexion MQTT)");
  
  // DHT
  Serial.print("[SETUP] Iniciando DHT22 en pin ");
  Serial.println(DHTPIN);
  dht.begin();
  Serial.println("[SETUP] DHT22 inicializado");
  
  // Sensor LDR
  pinMode(LDR_PIN, INPUT);
  Serial.print("[SETUP] LDR configurado en pin analogico ");
  Serial.println(LDR_PIN);
  
  // WiFi
  printDivider();
  Serial.println("[SETUP] --- FASE 1: WIFI ---");
  connectWiFi();
  
  // MQTT
  printDivider();
  Serial.println("[SETUP] --- FASE 2: MQTT ---");
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setKeepAlive(60);
  connectMQTT();
  
  // Test de sensores
  printDivider();
  Serial.println("[SETUP] --- TEST SENSORES ---");
  float t, h;
  readDHT(t, h);
  float l = readLux();
  Serial.println("[SETUP] Test sensores completado");
  
  printDivider();
  Serial.println("[SETUP] ===== SETUP COMPLETO =====");
  Serial.println("[SETUP] Dispositivo listo para loop()");
  printDivider();
}

// ============ LOOP ============
void loop() {
  loopCount++;
  
  printDivider();
  Serial.print("[LOOP] Iteracion #");
  Serial.println(loopCount);
  
  // Mantener conexion MQTT
  if (!mqttClient.connected()) {
    Serial.println("[LOOP] MQTT desconectado - reconectando...");
    digitalWrite(LED_PIN, LOW);
    connectMQTT();
  } else {
    Serial.println("[LOOP] MQTT conectado - OK");
    mqttClient.loop();
  }
  
  // Lectura sensores
  printDivider();
  Serial.println("[LOOP] --- LEYENDO SENSORES ---");
  
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  float lux = readLux();
  
  if (isnan(h) || isnan(t)) {
    Serial.println("[LOOP] ✗ Error leyendo DHT22");
    Serial.println("[LOOP] Intentando re-inicializar DHT...");
    dht.begin();
  } else {
    printDivider();
    Serial.println("[LOOP] --- PUBLICANDO DATOS ---");
    Serial.print("[LOOP] Temperatura: ");
    Serial.print(t, 1);
    Serial.println(" C");
    Serial.print("[LOOP] Humedad: ");
    Serial.print(h, 1);
    Serial.println(" %");
    Serial.print("[LOOP] Luminosidad: ");
    Serial.print(lux, 1);
    Serial.println(" lux");
    
    publishData(t, h, lux);
  }
  
  printDivider();
  Serial.print("[LOOP] Durmiendo 30s... proxima lectura en ");
  Serial.print(millis() / 1000);
  Serial.println("s");
  printDivider();
  
  delay(30000);
}
/*
  D2 - Meteo patio/cubierta - Campus UNAB
  Wokwi ESP32: DHT22 + LDR + LED + MQTT

  Publica:
    campus/ems/D2      → telemetria  {"temperature":..,"humidity":..,"lux":..,"source":"wokwi-d2"}
    campus/ems/D2/log  → log de texto (una linea por evento, mismo texto del Serial Monitor)

  El bridge (python/mqtt_bridge_wokwi.py) reenvia la telemetria a Azure IoT Central y
  guarda las lineas de log en ~/iotlogs/wokwi_d2.log, que el dashboard muestra en vivo.

  Version de firmware: D2-FW 1.1 (agrega publicacion de logs por MQTT)
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

#define FW_VERSION "D2-FW 1.2"

// --- Configuracion WiFi (Wokwi-GUEST para simulador) ---
const char* ssid     = "Wokwi-GUEST";
const char* password = "";

// --- Configuracion MQTT ---
const char* mqtt_server  = "test.mosquitto.org";
const int   mqtt_port    = 1883;
const char* mqtt_topic   = "campus/ems/D2";
const char* mqtt_log     = "campus/ems/D2/log";
const char* client_id    = "campus-ems-02";

// --- Sensores ---
#define DHTPIN  4
#define DHTTYPE DHT22
#define LDR_PIN 34
#define LED_PIN 2

// --- Botones de trigger (Wokwi) ---
#define BTN_TEMP_PIN   5   // GPIO5  -> BOTON A: spike de temperatura
#define BTN_ASESOR_PIN 18  // GPIO18 -> BOTON B: llamar asesor
#define TEMP_SPIKE_OFFSET 12.0  // grados que se suman en el spike

// Curva del fotorresistor (valores tipicos del modulo wokwi-photoresistor-sensor):
// RL10 = resistencia a 10 lux, GAMMA = pendiente log-log de la curva lux/resistencia.
// Sin estos dos defines el sketch no compilaba.
#define LDR_RL10  50.0
#define LDR_GAMMA 0.7

DHT dht(DHTPIN, DHTTYPE);

WiFiClient   espClient;
PubSubClient mqttClient(espClient);

unsigned long loopCount    = 0;
unsigned long bootMillis   = 0;
int           logDropped   = 0;

// --- Estado botones / debounce ---
bool  lastBtnTemp   = HIGH;
bool  lastBtnAsesor = HIGH;
unsigned long lastBtnTempDebounce   = 0;
unsigned long lastBtnAsesorDebounce = 0;
const unsigned long DEBOUNCE_MS = 50;
float tempSpikeRemaining = 0.0;   // >0 => spike de temperatura activo por N ciclos

void printDivider() {
  Serial.println("========================================");
}

// ---------------------------------------------------------------------------
// LOG: imprime en el Serial Monitor Y publica la misma linea por MQTT al
// topico de logs. Asi el dashboard ve el serial de Wokwi sin depender de que
// la simulacion corra en el mismo equipo que el dashboard.
// ---------------------------------------------------------------------------
void LOG(const String &msg) {
  Serial.println(msg);
  if (!mqttClient.connected()) {
    return;
  }
  if (!mqttClient.publish(mqtt_log, msg.c_str())) {
    logDropped++;
  }
}

void LOG1(const char *a, const String &b) {
  LOG(String(a) + b);
}

// ============ WIFI ============
void connectWiFi() {
  LOG("[WIFI] Iniciando conexion...");
  LOG1("[WIFI] SSID: ", ssid);

  WiFi.begin(ssid, password);

  int attempts = 0;
  Serial.print("[WIFI] Intentando conectar");
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    printDivider();
    LOG("[WIFI] OK - CONEXION EXITOSA");
    LOG1("[WIFI] IP local: ", WiFi.localIP().toString());
    LOG1("[WIFI] Gateway: ", WiFi.gatewayIP().toString());
    LOG1("[WIFI] RSSI: ", String(WiFi.RSSI()) + " dBm");
    printDivider();
  } else {
    LOG("[WIFI] FALLO - continuando sin red");
  }
}

// ============ MQTT ============
void connectMQTT() {
  LOG("[MQTT] Iniciando conexion a broker...");
  LOG1("[MQTT] Server: ", mqtt_server);
  LOG1("[MQTT] Topic telemetria: ", mqtt_topic);
  LOG1("[MQTT] Topic logs: ", mqtt_log);
  LOG1("[MQTT] Client ID: ", client_id);

  int attempts = 0;
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Intento ");
    Serial.print(++attempts);
    Serial.print("... ");

    if (mqttClient.connect(client_id)) {
      Serial.println("OK");
      digitalWrite(LED_PIN, HIGH);
      printDivider();
      LOG("[MQTT] OK - CONEXION EXITOSA AL BROKER");
      LOG1("[MQTT] Estado: ", String(mqttClient.state()));
      LOG1("[MQTT] Uptime ms: ", String(millis()));
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

  if (voltage <= 0.001) voltage = 0.001;
  if (voltage >= 3.299) voltage = 3.299;

  float resistance = 10000.0 * (3.3 - voltage) / voltage;
  if (!isfinite(resistance) || resistance <= 0) {
    LOG("[LDR] error de resistencia - retornando 0");
    return 0.0;
  }

  float lux = pow(LDR_RL10 * 1e3 * pow(10.0, LDR_GAMMA) / resistance, 1.0 / LDR_GAMMA);
  if (!isfinite(lux)) {
    LOG("[LDR] error de calculo de lux - retornando 0");
    return 0.0;
  }

  LOG("[LDR] ADC=" + String(analogValue) + " V=" + String(voltage, 3) +
      " R=" + String(resistance, 1) + "ohm lux=" + String(lux, 1));
  return lux;
}

void readDHT(float &temp, float &hum) {
  hum  = dht.readHumidity();
  temp = dht.readTemperature();

  LOG("[DHT22] temperatura=" + (isnan(temp) ? String("ERROR") : String(temp, 1) + "C") +
      " humedad=" + (isnan(hum) ? String("ERROR") : String(hum, 1) + "%"));
}

// ============ PUBLICAR ============
void publishData(float temp, float hum, float lux) {
  char payload[160];
  snprintf(payload, sizeof(payload),
           "{\"temperature\":%.1f,\"humidity\":%.1f,\"lux\":%.1f,\"source\":\"wokwi-d2\"}",
           temp, hum, lux);

  LOG1("[PUB] payload: ", payload);

  bool ok = mqttClient.publish(mqtt_topic, payload);
  LOG(ok ? "[PUB] OK - mensaje publicado" : "[PUB] ERROR - no se pudo publicar");
}

// ============ TRIGGERS (BOTONES) ============
// BOTON A: spike de temperatura (simula alarma de calor).
void triggerTempSpike() {
  tempSpikeRemaining = 3;  // activo durante los proximos 3 ciclos
  printDivider();
  LOG("[TRIGGER] ===== SPIKE DE TEMPERATURA ===== (BOTON A)");
  LOG("[TRIGGER] Alarma de calor activada, inyectando pico de temperatura");
  LOG1("[TRIGGER] Offset aplicado: +", String(TEMP_SPIKE_OFFSET) + " C");
  printDivider();
}

// BOTON B: llamar asesor (envia evento a consola/log).
void triggerCallAdvisor() {
  printDivider();
  LOG("[TRIGGER] ===== LLAMAR ASESOR ===== (BOTON B)");
  LOG("[TRIGGER] hola, soy un boton - llamar asesor");
  LOG("[TRIGGER] Solicitando asistencia al asesor de campus...");
  if (mqttClient.connected()) {
    const char* evt = "{\"event\":\"call_advisor\",\"message\":\"hola, soy un boton - llamar asesor\",\"source\":\"wokwi-d2\"}";
    mqttClient.publish("campus/ems/D2/event", evt);
    LOG1("[TRIGGER] Evento publicado: ", evt);
  } else {
    LOG("[TRIGGER] MQTT no conectado - evento solo en consola");
  }
  printDivider();
}

// Lee ambos botones con debounce y dispara los triggers en flanco de bajada.
void checkButtons() {
  unsigned long now = millis();

  bool btnTemp   = digitalRead(BTN_TEMP_PIN);
  bool btnAsesor = digitalRead(BTN_ASESOR_PIN);

  if (btnTemp != lastBtnTemp && (now - lastBtnTempDebounce) > DEBOUNCE_MS) {
    lastBtnTempDebounce = now;
    lastBtnTemp = btnTemp;
    if (btnTemp == LOW) {
      LOG("[BTN] BOTON A (SPIKE TEMP) presionado");
      triggerTempSpike();
    }
  }

  if (btnAsesor != lastBtnAsesor && (now - lastBtnAsesorDebounce) > DEBOUNCE_MS) {
    lastBtnAsesorDebounce = now;
    lastBtnAsesor = btnAsesor;
    if (btnAsesor == LOW) {
      LOG("[BTN] BOTON B (LLAMAR ASESOR) presionado");
      triggerCallAdvisor();
    }
  }
}

// ============ SETUP ============
void setup() {
  Serial.begin(115200);
  delay(500);
  bootMillis = millis();

  printDivider();
  LOG(String("[SETUP] ===== INICIANDO ESP32 D2 ====="));
  LOG1("[SETUP] firmware: ", FW_VERSION);
  LOG("[SETUP] Campus UNAB - Wokwi ESP32 Simulator");
  printDivider();

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  LOG("[SETUP] LED OFF (esperando conexion MQTT)");

  LOG1("[SETUP] iniciando DHT22 en pin ", String(DHTPIN));
  dht.begin();
  LOG("[SETUP] DHT22 inicializado");

  pinMode(LDR_PIN, INPUT);
  LOG1("[SETUP] LDR configurado en pin analogico ", String(LDR_PIN));

  pinMode(BTN_TEMP_PIN, INPUT_PULLUP);
  pinMode(BTN_ASESOR_PIN, INPUT_PULLUP);
  LOG("[SETUP] Botones configurados (INPUT_PULLUP)");
  LOG1("[SETUP] BOTON A (spike temp) en pin D", String(BTN_TEMP_PIN));
  LOG1("[SETUP] BOTON B (llamar asesor) en pin D", String(BTN_ASESOR_PIN));

  printDivider();
  LOG("[SETUP] --- FASE 1: WIFI ---");
  connectWiFi();

  printDivider();
  LOG("[SETUP] --- FASE 2: MQTT ---");
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setKeepAlive(60);
  mqttClient.setBufferSize(512);
  connectMQTT();

  printDivider();
  LOG("[SETUP] --- TEST SENSORES ---");
  float t, h;
  readDHT(t, h);
  float l = readLux();
  LOG1("[SETUP] test completado, lux=", String(l, 1));

  printDivider();
  LOG("[SETUP] ===== SETUP COMPLETO =====");
  printDivider();
}

// ============ LOOP ============
void loop() {
  loopCount++;

  LOG1("[LOOP] iteracion #", String(loopCount));

  if (!mqttClient.connected()) {
    LOG("[LOOP] MQTT desconectado - reconectando...");
    digitalWrite(LED_PIN, LOW);
    connectMQTT();
  } else {
    LOG("[LOOP] MQTT conectado - OK");
    mqttClient.loop();
  }

  LOG("[LOOP] --- leyendo sensores ---");
  checkButtons();

  float h = dht.readHumidity();
  float t = dht.readTemperature();
  float lux = readLux();

  if (isnan(h) || isnan(t)) {
    LOG("[LOOP] ERROR leyendo DHT22 - re-inicializando sensor");
    dht.begin();
  } else {
    // Aplicar spike de temperatura si BOTON A fue presionado recientemente.
    if (tempSpikeRemaining > 0) {
      t += TEMP_SPIKE_OFFSET;
      tempSpikeRemaining--;
      LOG1("[LOOP] *** SPIKE ACTIVO *** temperatura inyectada: ", String(t, 1) + " C (quedan " + String(tempSpikeRemaining) + " ciclos)");
    }

    LOG("[LOOP] --- publicando datos ---");
    LOG1("[LOOP] temperatura: ", String(t, 1) + " C");
    LOG1("[LOOP] humedad: ", String(h, 1) + " %");
    LOG1("[LOOP] luminosidad: ", String(lux, 1) + " lux");
    publishData(t, h, lux);
  }

  LOG1("[LOOP] uptime=", String(millis() / 1000) + "s logs_perdidos=" + String(logDropped));
  LOG("[LOOP] durmiendo 30s...");

  delay(30000);
}

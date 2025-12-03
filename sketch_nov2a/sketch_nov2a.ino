#include <WiFi.h>
#include <PubSubClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ====== KONFIGURASI WIFI & MQTT ======
const char* ssid = "SamsungA36";         // Ganti dengan nama WiFi kamu
const char* password = "adrifavianwifi";    // Ganti dengan password WiFi kamu
const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* mqtt_topic = "edukit/suhu";

// ====== PIN SENSOR ======
#define ONE_WIRE_BUS 4  // Pin data DS18B20 dihubungkan ke GPIO4
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// ====== MQTT CLIENT ======
WiFiClient espClient;
PubSubClient client(espClient);

// ====== MODE OFFLINE / ONLINE ======
bool offlineMode = false; // ubah ke true untuk mode offline (tanpa MQTT)

// ====== KONEKSI WIFI ======
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Menghubungkan ke WiFi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi terhubung!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nGagal terhubung ke WiFi. Masuk mode offline.");
    offlineMode = true;
  }
}

// ====== KONEKSI MQTT ======
void reconnect() {
  while (!client.connected()) {
    Serial.print("Menghubungkan ke MQTT...");
    if (client.connect("ESP32Client")) {
      Serial.println("Terhubung!");
    } else {
      Serial.print("Gagal, rc=");
      Serial.print(client.state());
      Serial.println(" Coba lagi dalam 5 detik...");
      delay(5000);
    }
  }
}

// ====== SETUP ======
void setup() {
  Serial.begin(115200);
  sensors.begin();
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  Serial.println("=== Edukit Suhu & Kalor Asas Black ===");
}

// ====== LOOP UTAMA ======
void loop() {
  sensors.requestTemperatures();
  float tempC = sensors.getTempCByIndex(0);
  if (tempC == DEVICE_DISCONNECTED_C) {
    Serial.println("Sensor tidak terdeteksi!");
    delay(2000);
    return;
  }

  // Konversi ke berbagai satuan
  float tempF = (tempC * 9 / 5) + 32;
  float tempK = tempC + 273.15;
  float tempR = tempC * 4 / 5;

  // Tampilkan ke Serial Monitor
  Serial.print("Celsius: "); Serial.print(tempC);
  Serial.print(" | Fahrenheit: "); Serial.print(tempF);
  Serial.print(" | Kelvin: "); Serial.print(tempK);
  Serial.print(" | Reamur: "); Serial.println(tempR);

  // Kirim ke MQTT (jika online)
  if (!offlineMode) {
    if (!client.connected()) reconnect();
    client.loop();

    // Format data ke JSON
    String payload = "{\"C\":" + String(tempC, 2) +
                     ",\"F\":" + String(tempF, 2) +
                     ",\"K\":" + String(tempK, 2) +
                     ",\"R\":" + String(tempR, 2) + "}";

    // Publish ke broker HiveMQ
    client.publish(mqtt_topic, payload.c_str());
    Serial.println("Data terkirim ke MQTT!");
  }

  delay(2000); // jeda 2 detik
}


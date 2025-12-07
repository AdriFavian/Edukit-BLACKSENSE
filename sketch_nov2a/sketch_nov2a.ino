#include <WiFi.h>
#include <PubSubClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ====== KONFIGURASI WIFI & MQTT ======
const char* ssid = "baksoikan";         // Ganti dengan nama WiFi kamu
const char* password = "baksoikansalmon";    // Ganti dengan password WiFi sekarang
const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* mqtt_topic = "edukit/suhu";

// ====== PIN SENSOR (3 Sensor DS18B20) ======
// Menggunakan 3 pin terpisah untuk masing-masing sensor
#define ONE_WIRE_BUS_DINGIN 4   // Sensor Air Dingin - GPIO4
#define ONE_WIRE_BUS_PANAS 5    // Sensor Air Panas - GPIO5
#define ONE_WIRE_BUS_CAMPURAN 18 // Sensor Air Campuran - GPIO18

// Inisialisasi OneWire dan DallasTemperature untuk setiap sensor
OneWire oneWireDingin(ONE_WIRE_BUS_DINGIN);
OneWire oneWirePanas(ONE_WIRE_BUS_PANAS);
OneWire oneWireCampuran(ONE_WIRE_BUS_CAMPURAN);

DallasTemperature sensorDingin(&oneWireDingin);
DallasTemperature sensorPanas(&oneWirePanas);
DallasTemperature sensorCampuran(&oneWireCampuran);

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
  
  // Inisialisasi ketiga sensor
  sensorDingin.begin();
  sensorPanas.begin();
  sensorCampuran.begin();
  
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  Serial.println("=== Edukit Suhu & Kalor Asas Black (3 Sensor) ===");
  Serial.println("Sensor 1: Air Dingin (GPIO4)");
  Serial.println("Sensor 2: Air Panas (GPIO5)");
  Serial.println("Sensor 3: Air Campuran (GPIO18)");
}

// ====== FUNGSI KONVERSI SUHU ======
void konversiSuhu(float tempC, float &tempF, float &tempK, float &tempR) {
  tempF = (tempC * 9.0 / 5.0) + 32.0;
  tempK = tempC + 273.15;
  tempR = tempC * 4.0 / 5.0;
}

// ====== LOOP UTAMA ======
void loop() {
  // Request suhu dari ketiga sensor
  sensorDingin.requestTemperatures();
  sensorPanas.requestTemperatures();
  sensorCampuran.requestTemperatures();
  
  // Baca suhu Celsius dari masing-masing sensor
  float tempC_dingin = sensorDingin.getTempCByIndex(0);
  float tempC_panas = sensorPanas.getTempCByIndex(0);
  float tempC_campuran = sensorCampuran.getTempCByIndex(0);
  
  // Cek apakah sensor terdeteksi
  bool sensorOK = true;
  if (tempC_dingin == DEVICE_DISCONNECTED_C) {
    Serial.println("Sensor Air Dingin tidak terdeteksi!");
    sensorOK = false;
  }
  if (tempC_panas == DEVICE_DISCONNECTED_C) {
    Serial.println("Sensor Air Panas tidak terdeteksi!");
    sensorOK = false;
  }
  if (tempC_campuran == DEVICE_DISCONNECTED_C) {
    Serial.println("Sensor Air Campuran tidak terdeteksi!");
    sensorOK = false;
  }
  
  if (!sensorOK) {
    delay(2000);
    return;
  }

  // Konversi suhu untuk sensor Air Dingin
  float tempF_dingin, tempK_dingin, tempR_dingin;
  konversiSuhu(tempC_dingin, tempF_dingin, tempK_dingin, tempR_dingin);
  
  // Konversi suhu untuk sensor Air Panas
  float tempF_panas, tempK_panas, tempR_panas;
  konversiSuhu(tempC_panas, tempF_panas, tempK_panas, tempR_panas);
  
  // Konversi suhu untuk sensor Air Campuran
  float tempF_campuran, tempK_campuran, tempR_campuran;
  konversiSuhu(tempC_campuran, tempF_campuran, tempK_campuran, tempR_campuran);

  // Tampilkan ke Serial Monitor
  Serial.println("========== DATA SUHU ==========");
  Serial.println("--- Air Dingin ---");
  Serial.print("  C: "); Serial.print(tempC_dingin);
  Serial.print(" | F: "); Serial.print(tempF_dingin);
  Serial.print(" | K: "); Serial.print(tempK_dingin);
  Serial.print(" | R: "); Serial.println(tempR_dingin);
  
  Serial.println("--- Air Panas ---");
  Serial.print("  C: "); Serial.print(tempC_panas);
  Serial.print(" | F: "); Serial.print(tempF_panas);
  Serial.print(" | K: "); Serial.print(tempK_panas);
  Serial.print(" | R: "); Serial.println(tempR_panas);
  
  Serial.println("--- Air Campuran ---");
  Serial.print("  C: "); Serial.print(tempC_campuran);
  Serial.print(" | F: "); Serial.print(tempF_campuran);
  Serial.print(" | K: "); Serial.print(tempK_campuran);
  Serial.print(" | R: "); Serial.println(tempR_campuran);
  Serial.println("================================");

  // Kirim ke MQTT (jika online)
  if (!offlineMode) {
    if (!client.connected()) reconnect();
    client.loop();

    // Format data ke JSON dengan struktur nested untuk 3 sensor
    String payload = "{";
    payload += "\"dingin\":{";
    payload += "\"C\":" + String(tempC_dingin, 2) + ",";
    payload += "\"F\":" + String(tempF_dingin, 2) + ",";
    payload += "\"K\":" + String(tempK_dingin, 2) + ",";
    payload += "\"R\":" + String(tempR_dingin, 2) + "},";
    
    payload += "\"panas\":{";
    payload += "\"C\":" + String(tempC_panas, 2) + ",";
    payload += "\"F\":" + String(tempF_panas, 2) + ",";
    payload += "\"K\":" + String(tempK_panas, 2) + ",";
    payload += "\"R\":" + String(tempR_panas, 2) + "},";
    
    payload += "\"campuran\":{";
    payload += "\"C\":" + String(tempC_campuran, 2) + ",";
    payload += "\"F\":" + String(tempF_campuran, 2) + ",";
    payload += "\"K\":" + String(tempK_campuran, 2) + ",";
    payload += "\"R\":" + String(tempR_campuran, 2) + "}";
    payload += "}";

    // Publish ke broker HiveMQ
    client.publish(mqtt_topic, payload.c_str());
    Serial.println("Data terkirim ke MQTT!");
  }

  delay(2000); // jeda 2 detik
}


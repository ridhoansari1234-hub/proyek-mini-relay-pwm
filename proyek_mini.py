"""
Proyek Mini - Dashboard Node-RED untuk Kontrol Relay dan Monitoring Suhu
NIM : 2410020167

Simulasi perangkat ESP32 dengan Python:
1. Mengirim data suhu DHT22 setiap 3 detik
2. Menerima perintah relay ("ON"/"OFF") dan mengendalikan GPIO 26
3. Menerima nilai PWM (0-255) dan mengendalikan kecerahan LED pada GPIO 2
"""

import time
import random
import threading
import paho.mqtt.client as mqtt

# ================= KONFIGURASI =================
NIM = "2410020167"

MQTT_BROKER = "localhost"  # Mosquitto lokal
MQTT_PORT = 1883
MQTT_CLIENT_ID = f"PythonDevice-{NIM}"

TOPIC_SUHU = f"iot/{NIM}/sensor/suhu"
TOPIC_RELAY = f"iot/{NIM}/aktuator/relay"
TOPIC_PWM = f"iot/{NIM}/aktuator/pwm"
TOPIC_STATUS_RELAY = f"iot/{NIM}/status/relay"  # feedback status relay
TOPIC_STATUS_PWM = f"iot/{NIM}/status/pwm"      # feedback nilai PWM

PIN_RELAY = 26  # GPIO 26 -> relay
PIN_LED = 2     # GPIO 2  -> LED (PWM)

INTERVAL_PUBLISH = 3  # detik

# ================= STATE GLOBAL =================
relay_state = "OFF"
pwm_value = 0


# ================= AKTUATOR =================
def set_relay(state):
    """Kendalikan relay pada GPIO 26 (simulasi).
    Perangkat asli (ESP32): digitalWrite(26, state == "ON" ? HIGH : LOW);"""
    level = "HIGH" if state == "ON" else "LOW"
    print(f"[RELAY] GPIO {PIN_RELAY} -> {level} (relay {state})")


def set_pwm(value):
    """Atur kecerahan LED pada GPIO 2 (simulasi).
    Perangkat asli (ESP32): ledcWrite(channel, value);"""
    persen = round(value / 255 * 100)
    print(f"[PWM] GPIO {PIN_LED} -> duty {value}/255 (kecerahan {persen}%)")


# ================= CALLBACK MQTT =================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Terhubung ke broker")
        client.subscribe([(TOPIC_RELAY, 0), (TOPIC_PWM, 0)])
        print(f"[MQTT] Subscribe ke topik: {TOPIC_RELAY}")
        print(f"[MQTT] Subscribe ke topik: {TOPIC_PWM}")
    else:
        print(f"[MQTT] Gagal terhubung, kode: {rc}")


def on_message(client, userdata, msg):
    """Dipanggil setiap ada pesan pada topik yang di-subscribe."""
    global relay_state, pwm_value
    payload = msg.payload.decode("utf-8", errors="replace").strip()
    print(f"[MQTT] Pesan masuk [{msg.topic}]: {payload}")

    if msg.topic == TOPIC_RELAY:
        perintah = payload.upper()
        if perintah not in ("ON", "OFF"):
            print(f"[RELAY] Perintah tidak dikenal: {payload}")
            return
        relay_state = perintah
        set_relay(relay_state)
        client.publish(TOPIC_STATUS_RELAY, relay_state, qos=0)
        print(f"[MQTT] Publish status: {TOPIC_STATUS_RELAY} -> {relay_state}")

    elif msg.topic == TOPIC_PWM:
        try:
            nilai = int(float(payload))
        except ValueError:
            print(f"[PWM] Nilai bukan angka: {payload}")
            return
        if not 0 <= nilai <= 255:
            print(f"[PWM] Nilai di luar rentang 0-255: {nilai}")
            return
        pwm_value = nilai
        set_pwm(pwm_value)
        client.publish(TOPIC_STATUS_PWM, str(pwm_value), qos=0)
        print(f"[MQTT] Publish status: {TOPIC_STATUS_PWM} -> {pwm_value}")


def on_disconnect(client, userdata, rc):
    print(f"[MQTT] Terputus (kode: {rc}). Mencoba reconnect...")


# ================= PEMBACAAN SENSOR =================
def baca_suhu():
    """
    Simulasi pembacaan suhu DHT22.
    Jika memakai DHT22 asli di Raspberry Pi, ganti dengan:
        import board, adafruit_dht
        dht = adafruit_dht.DHT22(board.D4)
        return round(dht.temperature, 2)
    Jika memakai ESP32: dht.readTemperature() pada library DHT sensor.
    """
    # Simulasi: suhu acak antara 25.5 - 28.5 C dengan fluktuasi halus
    base = 27.0
    noise = random.uniform(-1.5, 1.5)
    return round(base + noise, 2)


# ================= THREAD PUBLISH SENSOR =================
def publish_loop(client):
    """Kirim data suhu setiap INTERVAL_PUBLISH detik."""
    while True:
        suhu = baca_suhu()
        if suhu is not None:
            client.publish(TOPIC_SUHU, str(suhu), qos=0)
            print(f"[SENSOR] Publish suhu: {TOPIC_SUHU} -> {suhu} °C")
        time.sleep(INTERVAL_PUBLISH)


# ================= MAIN =================
def main():
    # paho-mqtt 2.x mewajibkan callback_api_version; callback di atas bergaya VERSION1
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    print(f"[MQTT] Menghubungkan ke {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

    client.loop_start()
    time.sleep(1)

    publisher = threading.Thread(target=publish_loop, args=(client,), daemon=True)
    publisher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MAIN] Menghentikan program...")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()

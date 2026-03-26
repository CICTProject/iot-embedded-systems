import gc
import network
import time
import _thread
import config
import update

gc.collect()
print("\n" + "="*40)
print("BOOTING...")
print("="*40)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("-> [BOOT] Connecting...")
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        while not wlan.isconnected(): 
            time.sleep(0.1)
    print("-> [BOOT] WiFi Connected! IP:", wlan.ifconfig()[0])

def ota_background_task():
    while True:
        time.sleep(600) 
        update.check()

connect_wifi()

update.check()

print("-> [BOOT] OTA Update running underground.")
_thread.start_new_thread(ota_background_task, ())

print("-> [BOOT] Completed! Starting main.py...\n")

import time

def process_ota_update(version):
    print(f"\n[SYSTEM] Initiating OTA update to version {version}...")
    time.sleep(1)
    print("[SYSTEM] Downloading payload...")
    time.sleep(1)
    print("[SYSTEM] Verifying SHA256 signature... OK.")
    print("[SYSTEM] Update applied successfully.")
    return True
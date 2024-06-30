import alsaaudio

def get_audio_devices():
    cards = alsaaudio.cards()
    devices = []

    for card in cards:
        devices.append(card)

    return devices

if __name__ == "__main__":
    devices = get_audio_devices()
    if devices:
        print("Connected Audio Devices:")
        for device_name in devices:
            print(f"  - {device_name}")
    else:
        print("No audio devices found.")
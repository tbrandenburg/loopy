import mido

def list_midi_ports():
    """Listet verfügbare MIDI-Ports auf."""
    print("Verfügbare MIDI-Eingangsports:")
    for port in mido.get_input_names():
        print(f"  - {port}")

def read_midi_input(port_name):
    """Liest MIDI-Eingaben von einem spezifischen MIDI-Port."""
    with mido.open_input(port_name) as port:
        print(f"Listening for MIDI input on {port_name}...")
        for message in port:
            print(message)

if __name__ == "__main__":
    # Zeige verfügbare MIDI-Ports
    list_midi_ports()

    # Ersetze dies mit dem Namen deines AKAI MIDI-Ports
    selected_port = input("Gib den Namen des MIDI-Ports ein, um Daten zu lesen: ").strip()

    # Lese MIDI-Nachrichten
    read_midi_input(selected_port)

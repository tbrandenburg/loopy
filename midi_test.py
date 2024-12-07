import mido
import threading

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
            print(f"[{port_name}] {message}")

def read_all_midi_ports():
    """Liest MIDI-Daten von allen verfügbaren Ports aus."""
    input_ports = mido.get_input_names()
    if not input_ports:
        print("Keine MIDI-Eingangsports gefunden!")
        return

    threads = []
    for port_name in input_ports:
        thread = threading.Thread(target=read_midi_input, args=(port_name,))
        threads.append(thread)
        thread.start()

    # Threads laufen lassen, bis alle beendet sind (manuell abbrechen)
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    # Zeige verfügbare MIDI-Ports
    list_midi_ports()

    # MIDI-Daten von allen verfügbaren Ports lesen
    print("\nStarte das Lesen von allen MIDI-Ports...")
    read_all_midi_ports()

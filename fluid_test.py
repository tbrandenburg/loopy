import mido
import fluidsynth
import threading

# FluidSynth Setup
SOUNDFONT_PATH = 'sf2/GeneralUser-GS.sf2'  # Ersetze dies mit dem Pfad zu deiner SoundFont-Datei

# Spielt eine Note ab und verwaltet die aktiven Noten
def play_midi_message(message, fs, active_notes):
    """Spielt die MIDI-Nachricht ab und verwaltet die aktiven Noten."""
    if message.type == "note_on" and message.velocity > 0:
        if message.note not in active_notes:
            print(f"Note on: {message.note}, Velocity: {message.velocity}")
            fs.noteon(0, message.note, message.velocity)
            active_notes.add(message.note)
    elif message.type in ["note_off", "note_on"] and message.velocity == 0:
        if message.note in active_notes:
            print(f"Note off: {message.note}")
            fs.noteoff(0, message.note)
            active_notes.remove(message.note)

# Liest MIDI-Eingaben von einem spezifischen MIDI-Port und spielt sie ab
def read_midi_input(port_name, fs):
    """Liest MIDI-Eingaben von einem spezifischen MIDI-Port und spielt sie ab."""
    active_notes = set()  # Set, um alle aktiven Noten zu verfolgen
    with mido.open_input(port_name) as port:
        print(f"Listening for MIDI input on {port_name}...")
        for message in port:
            play_midi_message(message, fs, active_notes)

# Liest von allen verfügbaren MIDI-Ports
def read_all_midi_ports(fs):
    """Liest MIDI-Daten von allen verfügbaren Ports aus."""
    input_ports = mido.get_input_names()
    if not input_ports:
        print("Keine MIDI-Eingangsports gefunden!")
        return

    threads = []
    for port_name in input_ports:
        thread = threading.Thread(target=read_midi_input, args=(port_name, fs))
        threads.append(thread)
        thread.start()

    # Threads laufen lassen, bis alle beendet sind (manuell abbrechen)
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    # Starte FluidSynth
    fs = fluidsynth.Synth()
    fs.start(driver="alsa")  # Oder "pulseaudio", je nach System
    sfid = fs.sfload(SOUNDFONT_PATH)  # Lade SoundFont-Datei
    fs.program_select(0, sfid, 0, 0)  # Wähle ein Programm (Instrument) aus

    # Zeige verfügbare MIDI-Ports
    print("Verfügbare MIDI-Eingangsports:")
    for port_name in mido.get_input_names():
        print(f"  - {port_name}")

    # Lese MIDI-Daten von allen verfügbaren Ports
    print("\nStarte das Abhören von MIDI-Daten auf allen verfügbaren Ports...")
    read_all_midi_ports(fs)

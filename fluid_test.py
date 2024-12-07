import mido
import fluidsynth

# FluidSynth Setup
SOUNDFONT_PATH = 'sf2/GeneralUser-GS.sf2'  # Ersetze dies mit dem Pfad zu deiner SoundFont-Datei
MIDI_BASE_NOTE = 69  # A4 (MIDI-Note 69)

def midi_note_to_frequency(note):
    """Berechnet die Frequenz einer MIDI-Note."""
    base_frequency = 440.0  # A4 (MIDI-Note 69)
    return base_frequency * (2 ** ((note - MIDI_BASE_NOTE) / 12))

def play_midi_message(message, fs):
    """Spielt die MIDI-Nachricht ab."""
    if message.type == "note_on" and message.velocity > 0:
        print(f"Note on: {message.note}, Velocity: {message.velocity}")
        fs.noteon(0, message.note, message.velocity)
    elif message.type in ["note_off", "note_on"] and message.velocity == 0:
        print(f"Note off: {message.note}")
        fs.noteoff(0, message.note)

def read_midi_input(port_name, fs):
    """Liest MIDI-Eingaben von einem spezifischen MIDI-Port und spielt sie ab."""
    with mido.open_input(port_name) as port:
        print(f"Listening for MIDI input on {port_name}...")
        for message in port:
            play_midi_message(message, fs)

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

    # Wähle den MIDI-Port aus (erster verfügbarer Port)
    selected_port = mido.get_input_names()[0]  # Erster verfügbarer Port
    print(f"\nStarte das Abhören von MIDI-Daten auf Port: {selected_port}")

    # Lese MIDI-Daten von dem ausgewählten Port
    read_midi_input(selected_port, fs)


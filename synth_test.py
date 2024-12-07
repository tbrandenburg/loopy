import mido
import threading
import numpy as np
import pygame

# Konfiguration für Tonhöhen
BASE_FREQUENCY = 440.0  # A4 (MIDI-Note 69)
MIDI_BASE_NOTE = 69     # Referenznote (A4)

# Dictionary zur Speicherung vorab erzeugter Sounds
sound_cache = {}

def midi_note_to_frequency(note):
    """Berechnet die Frequenz einer MIDI-Note."""
    return BASE_FREQUENCY * (2 ** ((note - MIDI_BASE_NOTE) / 12))

def generate_sine_wave(frequency, duration=1.0, sample_rate=44100, amplitude=32767):
    """Erzeugt eine Sinuswelle mit gegebener Frequenz und Dauer."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.int16)
    return wave

def preload_sounds():
    """Erzeugt und speichert Sinuswellen für alle MIDI-Noten."""
    global sound_cache
    print("Preloading sounds...")
    for note in range(128):  # MIDI-Notenbereich 0–127
        frequency = midi_note_to_frequency(note)
        wave = generate_sine_wave(frequency, duration=1.0)
        sound_cache[note] = pygame.sndarray.make_sound(wave)
    print("Sounds preloaded.")

def play_note(note):
    """Spielt die vorab erzeugte Sinuswelle für die gegebene Note."""
    if note in sound_cache:
        sound = sound_cache[note]
        sound.play()
    else:
        print(f"Note {note} not preloaded!")

def read_midi_input(port_name):
    """Liest MIDI-Eingaben von einem spezifischen MIDI-Port."""
    with mido.open_input(port_name) as port:
        print(f"Listening for MIDI input on {port_name}...")
        for message in port:
            if message.type == "note_on" and message.velocity > 0:
                play_note(message.note)
            elif message.type == "note_off" or (message.type == "note_on" and message.velocity == 0):
                print(f"Note off: {message.note}")

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
    print("Verfügbare MIDI-Eingangsports:")
    for port in mido.get_input_names():
        print(f"  - {port}")

    # Initialisiere pygame und lade Sounds vor
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    preload_sounds()

    # MIDI-Daten von allen Ports lesen
    print("\nStarte das Lesen von allen MIDI-Ports...")
    read_all_midi_ports()

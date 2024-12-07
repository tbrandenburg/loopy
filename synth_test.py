import mido
import threading
import pygame.mixer
import time

# Konfiguration für Tonhöhen
BASE_FREQUENCY = 440.0  # A4 (MIDI-Note 69)
MIDI_BASE_NOTE = 69     # Referenznote (A4)

def midi_note_to_frequency(note):
    """Berechnet die Frequenz einer MIDI-Note."""
    return BASE_FREQUENCY * (2 ** ((note - MIDI_BASE_NOTE) / 12))

def play_note(note, duration=0.5):
    """Erzeugt und spielt einen Ton für die gegebene Note."""
    frequency = midi_note_to_frequency(note)
    print(f"Playing note {note} (Frequency: {frequency:.2f} Hz)")

    # Initialisiere den Mixer (einmalig)
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    
    # Erzeuge eine Sinuswelle als Sound
    sample_rate = 44100
    samples = (
        int((2**15 - 1) * pygame.sndarray.make_sound(
            pygame.sndarray.array(
                [[int((2**15 - 1) * pygame.mixer.Sound.sin(frequency * t / sample_rate))
                  for t in range(int(sample_rate * duration))]]
            )
        ))
    )
    sound = pygame.mixer.Sound(samples)
    sound.play()
    time.sleep(duration)
    sound.stop()

def read_midi_input(port_name):
    """Liest MIDI-Eingaben von einem spezifischen MIDI-Port."""
    with mido.open_input(port_name) as port:
        print(f"Listening for MIDI input on {port_name}...")
        for message in port:
            if message.type == "note_on" and message.velocity > 0:
                # Spiele die Note
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

    print("\nStarte das Lesen von allen MIDI-Ports...")
    read_all_midi_ports()


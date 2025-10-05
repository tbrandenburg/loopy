import time
import threading
import fluidsynth
import sys

# FluidSynth Setup
SOUNDFONT_PATH = 'sf2/GeneralUser-GS.sf2'  # Ersetze dies mit dem Pfad zu deiner SoundFont-Datei

# Wähle den richtigen FluidSynth-Treiber basierend auf dem Betriebssystem
if sys.platform == "linux" or sys.platform == "linux2":
    DRIVER = "alsa"  # Linux: ALSA oder PulseAudio
elif sys.platform == "darwin":
    DRIVER = "coreaudio"  # macOS: CoreAudio
else:
    DRIVER = "default"  # Standardtreiber für andere Systeme

# Funktion zum Spielen eines einzelnen Schlages
def play_beat(is_accented, fs, note=60):
    """Spielt einen Schlag (Beat) ab. Wenn 'is_accented' wahr ist, gibt es einen Akzent auf dem Schlag."""
    velocity = 100 if is_accented else 80  # Akzentuierter Schlag hat höhere Lautstärke
    fs.noteon(0, note, velocity)
    time.sleep(0.1)  # Kurze Dauer des Schlages
    fs.noteoff(0, note)

# Funktion zum Abspielen des Metronoms mit einstellbarem BPM und Takt
def play_metronome(bpm, ticks_per_measure, fs):
    """Spielt das Metronom mit anpassbarem BPM und Takt."""
    seconds_per_beat = 60 / bpm  # Wie lange dauert ein Schlag (in Sekunden)
    while True:
        for i in range(ticks_per_measure):
            is_accented = (i == 0)  # Akzent auf dem ersten Schlag jedes Takts
            play_beat(is_accented, fs)
            time.sleep(seconds_per_beat)  # Warten bis zum nächsten Schlag

# Funktion zum Abrufen von Argumenten und Starten des Metronoms
def start_metronome():
    """Startet das Metronom mit benutzerdefinierten Parametern."""
    if len(sys.argv) != 3:
        print("Verwendung: python metronom.py <BPM> <Takt>")
        print("<Takt> sollte eine Zahl wie 4 (für 4/4-Takt) oder 3 (für 3/4-Takt) sein.")
        sys.exit(1)

    bpm = int(sys.argv[1])  # BPM als erstes Argument
    ticks_per_measure = int(sys.argv[2])  # Takt als zweites Argument (z. B. 4 für 4/4-Takt)

    # FluidSynth Setup
    fs = fluidsynth.Synth()
    fs.start(driver=DRIVER)  # Oder "pulseaudio", je nach System
    sfid = fs.sfload(SOUNDFONT_PATH)  # Lade SoundFont-Datei
    fs.program_select(0, sfid, 0, 0)  # Wähle ein Programm (Instrument) aus

    # Starte das Metronom in einem separaten Thread
    metronome_thread = threading.Thread(target=play_metronome, args=(bpm, ticks_per_measure, fs))
    metronome_thread.daemon = True  # Erlaubt das Beenden des Programms, ohne den Thread zu stoppen
    metronome_thread.start()

    # Program läuft, bis der Benutzer es manuell beendet
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Metronom gestoppt.")

# Starte das Metronom
if __name__ == "__main__":
    start_metronome()

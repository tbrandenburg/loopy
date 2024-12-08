import mido
import threading
import time
import fluidsynth
import sys

# Wähle den richtigen FluidSynth-Treiber basierend auf dem Betriebssystem
if sys.platform == "linux" or sys.platform == "linux2":
    DRIVER = "alsa"  # Linux: ALSA oder PulseAudio
elif sys.platform == "darwin":
    DRIVER = "coreaudio"  # macOS: CoreAudio
elif sys.platform == "win32":
    DRIVER = "dsound"  # Windows: DirectSound
else:
    DRIVER = "file"  # Fallback-Treiber

class InstrumentRegistry:
    """Verwaltet Instrumenten-IDs und ordnet sie den FluidSynth-SoundFonts zu."""
    
    def __init__(self, project):
        self._registry = {}  # Speichert Informationen über Instrumente und deren Synth-Instanzen
        self._soundfont_cache = {}  # Speichert geladene SoundFonts (Pfad -> sfid)
        self._fs = fluidsynth.Synth()
        self._fs.start(driver=DRIVER)  # Startet FluidSynth mit dem richtigen Treiber

    def get_synth(self):
        return self._fs

    def register_instrument(self, instrument_name, soundfont_path, bank=0, preset=0):
        """Registriert ein Instrument mit einem SoundFont und erstellt die Synth-Instanz."""
        
        # Prüfen, ob der SoundFont bereits geladen wurde
        if soundfont_path in self._soundfont_cache:
            sfid = self._soundfont_cache[soundfont_path]  # Verwende die vorhandene sfid
        else:
            sfid = self._fs.sfload(soundfont_path)  # Lade den SoundFont
            self._soundfont_cache[soundfont_path] = sfid  # Speichere die sfid im Cache

        # Wähle das Instrument (Programm) auf einem neuen Kanal
        # Finde den nächsten freien Kanal
        available_channel = len(self._registry) % 16  # Einfacher Round-Robin-Ansatz

        # Program auswählen und registrieren
        self._fs.program_select(available_channel, sfid, bank, preset)
        self._registry[instrument_name] = {
            "channel": available_channel,
            "sfid": sfid,
            "bank": bank,
            "preset": preset
        }

    def get_instrument(self, instrument_name):
        """Gibt die FluidSynth-Instanz und den Kanal des Instruments zurück."""
        instrument = self._registry.get(instrument_name)
        if instrument:
            return self._fs, instrument["channel"]
        return None, None

    def list_registered_instruments(self):
        """Gibt eine Liste aller registrierten Instrumente zurück."""
        return list(self._registry.keys())

class InstrumentChannel:
    """Abstrakte Basisklasse für alle Instrumentkanäle."""
    
    def __init__(self, project, instrument_name, volume=80):
        self._project = project
        self._instrument_name = instrument_name
        self._volume = volume
        self._instrument_registry = project.get_instrument_registry()  # Zugriff auf die Registry
        self._synth, self._channel = self._instrument_registry.get_instrument(instrument_name)  # Hole die Synth-Instanz
        self._is_playing = False

    def set_instrument(self, instrument_name):
        """Setzt das Instrument des Kanals anhand des Instrument-Namens."""
        self._instrument_name = instrument_name
        self._synth = self._instrument_registry.get_instrument(instrument_name)

    def set_volume(self, volume):
        """Setzt die Lautstärke des Kanals."""
        self._volume = volume

    def get_volume(self):
        """Gibt die Lautstärke des Kanals zurück."""
        return self._volume

    def play(self):
        """Startet den Kanal."""
        if not self._is_playing:
            print(f"Startet Kanal {self._instrument_name}...")
            self._is_playing = True

    def stop(self):
        """Stoppt den Kanal."""
        if self._is_playing:
            print(f"Pausiert Kanal {self._instrument_name}...")
            self._is_playing = False

    def tick(self):
        """Muss in Unterklassen implementiert werden, um auf den Takt zu reagieren."""
        raise NotImplementedError("Die Methode 'tick' muss in der Unterklasse implementiert werden.")

class FluidMidiChannel(InstrumentChannel):
    """Ein Kanal für MIDI-Eingabe und -Ausgabe mit FluidSynth und Polyphonie."""
    
    def __init__(self, project, port_name, instrument_name, volume=80):
        super().__init__(project, instrument_name, volume)
        self._port_name = port_name
        self._active_notes = set()

    def play(self):
        """Startet den Kanal und beginnt, MIDI-Daten zu empfangen."""
        super().play()  # Setze den Kanal auf "play"
        if self._is_playing:
            print(f"Beginne, MIDI-Daten auf Kanal {self._instrument_name} zu empfangen...")
            threading.Thread(target=self._read_midi_input, daemon=True).start()

    def stop(self):
        """Stoppt den Kanal und beendet alle laufenden Noten."""
        super().stop()  # Setze den Kanal auf "stop"
        if not self._is_playing:
            print(f"Beende das Abhören von MIDI-Daten auf Kanal {self._instrument_name}...")
            for note in self._active_notes:
                self._synth.noteoff(self._channel, note)
            self._active_notes.clear()

    def _play_midi_message(self, message):
        """Spielt eine MIDI-Nachricht ab und verwaltet die aktiven Noten."""
        if message.type == "note_on" and message.velocity > 0:
            if message.note not in self._active_notes:
                print(f"Note on: {message.note}, Velocity: {message.velocity}")
                self._synth.noteon(self._channel, message.note, message.velocity)
                self._active_notes.add(message.note)
        elif message.type in ["note_off", "note_on"] and message.velocity == 0:
            if message.note in self._active_notes:
                print(f"Note off: {message.note}")
                self._synth.noteoff(self._channel, message.note)
                self._active_notes.remove(message.note)

    def _read_midi_input(self):
        """Liest MIDI-Eingaben von einem spezifischen MIDI-Port und spielt sie ab."""
        with mido.open_input(self._port_name) as port:
            print(f"Listening for MIDI input on {self._port_name}...")
            for message in port:
                if self._is_playing:
                    self._play_midi_message(message)

class MetronomeChannel(InstrumentChannel):
    """Ein Kanal für das Metronom, das nur eine Note bei jedem Takt-Tick spielt, mit Akzentlogik."""
    
    def __init__(self, project, instrument_name, volume=100, accent_volume=127):
        super().__init__(project, instrument_name, volume)
        self._accent_volume = accent_volume  # Lautstärke des Akzents auf der ersten Zählzeit
        self._tick_count = 0  # Zählvariable für die Taktzählung

    def tick(self):
        """Reagiert auf den Takt-Tick und spielt eine Note mit Akzentlogik."""
        if self._is_playing:
            # Bestimme, ob dies die erste Zählzeit eines Taktes ist
            self._tick_count = (self._tick_count % self._project.get_ticks_per_measure()) + 1

            if self._tick_count == 1:
                # Akzent auf der ersten Zählzeit des Taktes (lauter)
                note = 60  # Beispiel-Note für den Schlag (kann geändert werden)
                velocity = self._accent_volume  # Lautstärke des Akzents
            else:
                # Normale Lautstärke für andere Zählzeiten
                note = 60  # Beispiel-Note für den Schlag
                velocity = self.get_volume()  # Normale Lautstärke

            # Spiele die Note für die Dauer von seconds_per_beat
            self._synth.noteon(self._channel, note, velocity)
            time.sleep(self._project.get_seconds_per_beat())  # Die Dauer der Note entspricht der Länge eines Beats
            self._synth.noteoff(self._channel, note)

class Project:
    """Das Projekt, das die Taktlogik verwaltet und Kanäle steuert."""
    
    def __init__(self, bpm=120, ticks_per_measure=4):
        self._instrument_registry = InstrumentRegistry(self)  # Verweis auf die InstrumentRegistry
        self._bpm = bpm
        self._ticks_per_measure = ticks_per_measure
        self._seconds_per_beat = 60 / bpm  # Berechne die Sekunden pro Schlag (für das Metronom)
        self._channels = []
        self._is_playing = False
        self._lock = threading.Lock()  # Für die Synchronisation der Takt-Ticks

    def get_instrument_registry(self):
        """Gibt die Instrument-Registry zurück."""
        return self._instrument_registry

    def get_bpm(self):
        """Gibt die BPM des Projekts zurück."""
        return self._bpm

    def get_ticks_per_measure(self):
        """Gibt die Ticks pro Takt des Projekts zurück."""
        return self._ticks_per_measure

    def get_seconds_per_beat(self):
        """Gibt die Sekunden pro Schlag zurück, basierend auf der BPM."""
        return self._seconds_per_beat

    def add_channel(self, channel):
        """Fügt dem Projekt einen Kanal hinzu."""
        self._channels.append(channel)

    def remove_channel(self, channel):
        """Entfernt einen Kanal aus dem Projekt."""
        self._channels.remove(channel)

    def start_ticking(self):
        """Startet das Takt-Management und benachrichtigt alle Kanäle."""
        self._is_playing = True
        while self._is_playing:
            with self._lock:
                for tick in range(self._ticks_per_measure):
                    # Benachrichtige alle Kanäle, dass ein Takt-Tick passiert ist
                    for channel in self._channels:
                        channel.tick()
                    time.sleep(self.get_seconds_per_beat())  # Warten bis zum nächsten Schlag

    def play(self):
        """Startet das Projekt und alle Kanäle."""
        threading.Thread(target=self.start_ticking).start()
        for channel in self._channels:
            channel.play()

    def stop(self):
        """Stoppt das Projekt und alle Kanäle."""
        self._is_playing = False
        for channel in self._channels:
            channel.stop()

# Beispielhafte Nutzung:

# Projekt mit BPM=120 und 4 Takt-Ticks pro Maß
projekt = Project(bpm=120, ticks_per_measure=4)

# Instrumente registrieren
projekt.get_instrument_registry().register_instrument("Piano", "sf2/GeneralUser-GS.sf2", 0, 0)
projekt.get_instrument_registry().register_instrument("Metronome", "sf2/GeneralUser-GS.sf2", 0, 0)

# Kanäle erstellen
for port_name in mido.get_input_names():
    fluid_midi_channel = FluidMidiChannel(projekt, port_name, "Piano")
    projekt.add_channel(fluid_midi_channel)
metronome_channel = MetronomeChannel(projekt, "Metronome", volume=100)
projekt.add_channel(metronome_channel)

# Starte das Projekt
projekt.play()

# Stoppe nach einer Weile (5 Sekunden) das Projekt
time.sleep(10)
projekt.stop()
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

        channel_info = self._fs.channel_info(available_channel)

        print(f"Registered '{channel_info[3]}' (bank={bank},preset={preset}) for FluidSynth channel {available_channel} and mapped to '{instrument_name}'!")

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
        self._volume = volume
        self._instrument_registry = project.get_instrument_registry()
        self.set_instrument(instrument_name)
        self._is_playing = False

    def set_instrument(self, instrument_name):
        """Setzt das Instrument des Kanals anhand des Instrument-Namens."""
        self._instrument_name = instrument_name
        self._synth, self._channel = self._instrument_registry.get_instrument(instrument_name)

    def set_volume(self, volume):
        """Setzt die Lautstärke des Kanals."""
        self._volume = volume

    def get_volume(self):
        """Gibt die Lautstärke des Kanals zurück."""
        return self._volume

    def play(self):
        """Startet den Kanal."""
        if not self._is_playing:
            print(f"Startet Kanal '{self}'...")
            self._is_playing = True

    def stop(self):
        """Stoppt den Kanal."""
        if self._is_playing:
            print(f"Pausiert Kanal '{self}'...")
            self._is_playing = False

    def tick(self):
        """Reaktion bei Taktschritt"""
        pass

class FreeMidiChannel(InstrumentChannel):
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

class FreeMetronomeChannel(InstrumentChannel):
    """Ein Kanal für das Metronom, das nur eine Note bei jedem Takt-Tick spielt, mit Akzentlogik."""
    
    def __init__(self, project, instrument_name, volume=100, accent_volume=127):
        super().__init__(project, instrument_name, volume)
        self._accent_volume = accent_volume  # Lautstärke des Akzents auf der ersten Zählzeit
        self._tick_count = 0  # Zählvariable für die Taktzählung

    def tick(self):
        """Reagiert auf den Takt-Tick und spielt eine Note mit Akzentlogik."""
        if self._is_playing:
            # Bestimme, ob dies die erste Zählzeit eines Taktes ist
            self._tick_count = (self._tick_count % self._project.get_beats_per_measure()) + 1

            if self._tick_count == 1:
                # Akzent auf der ersten Zählzeit des Taktes (lauter)
                note = 60  # Beispiel-Note für den Schlag (kann geändert werden)
                velocity = int(self._accent_volume*self._volume/100)  # Lautstärke des Akzents
            else:
                # Normale Lautstärke für andere Zählzeiten
                note = 60  # Beispiel-Note für den Schlag
                velocity = self.get_volume()  # Normale Lautstärke

            # Spiele die Note für die Dauer von seconds_per_beat
            self._synth.noteon(self._channel, note, velocity)
            time.sleep(self._project.get_seconds_per_beat())  # Die Dauer der Note entspricht der Länge eines Beats
            self._synth.noteoff(self._channel, note)

class StepSequencerChannel(InstrumentChannel):
    """Ein Kanal für einen Step-Sequencer."""
    
    def __init__(self, project, sequencer, volume=80):
        super().__init__(project, "", volume)
        self._sequencer = sequencer

    def play(self):
        """Startet den Kanal"""
        super().play()  # Setze den Kanal auf "play"
        if self._is_playing:
            self._sequencer.play()

    def stop(self):
        """Stoppt den Kanal"""
        super().stop()  # Setze den Kanal auf "stop"
        if not self._is_playing:
            self._sequencer.stop()

class StepChannel:
    """Abstrakte Basisklasse für alle Step-Kanäle."""
    
    def __init__(self, sequencer, instrument_name, volume=80):
        self._sequencer = sequencer
        self._instrument_name = instrument_name
        self._volume = volume
        self._is_playing = False
        self._steps = []

    def set_step(self, step, note, velocity):
        # Wenn der Schritt-Index größer als die aktuelle Liste ist, erweitere die Liste mit None
        if step >= len(self._steps):
            # Füge die erforderliche Anzahl an None-Werten hinzu, um den Index zu erreichen
            self._steps.extend([None] * (step + 1 - len(self._steps)))
        
        # Setze den Step mit der Note und der Velocity
        self._steps[step] = [note, velocity]


    def reset_step(self, step):
        # Wenn der Schritt-Index größer als die aktuelle Liste ist, erweitere die Liste mit None
        if step >= len(self._steps):
            # Füge die erforderliche Anzahl an None-Werten hinzu, um den Index zu erreichen
            self._steps.extend([None] * (step + 1 - len(self._steps)))
        
        # Setze den Step mit der Note und der Velocity
        self._steps[step] = None

    def set_instrument(self, instrument_name):
        """Setzt das Instrument des Kanals anhand des Instrument-Namens."""
        self._instrument_name = instrument_name

    def set_volume(self, volume):
        """Setzt die Lautstärke des Kanals."""
        self._volume = volume

    def get_volume(self):
        """Gibt die Lautstärke des Kanals zurück."""
        return self._volume

    def play(self):
        """Startet den Kanal."""
        if not self._is_playing:
            print(f"Startet Step-Kanal {self._instrument_name}...")
            self._is_playing = True

    def stop(self):
        """Stoppt den Kanal."""
        if self._is_playing:
            print(f"Pausiert Step-Kanal {self._instrument_name}...")
            self._is_playing = False

    def get_steps(self):
        return self._steps

class StepSequencer:
    """Sequencer der eigene Step-Kanäle tickweise abspielt"""

    def __init__(self, synth, bpm=120, steps=32, beats_per_measure=4):
        """Konstruktor"""
        self._synth = synth
        self._seq = fluidsynth.Sequencer(time_scale=1000, use_system_timer=False)
        self._synth_id = self._seq.register_fluidsynth(self._synth)
        self._step_callback_id = self._seq.register_client("stepCallback", self._step_callback)

        self._channels = []

        self._bpm = bpm
        self._beats_per_measure = beats_per_measure
        self._seconds_per_beat = 60 / bpm
        self._steps = steps
        self._is_playing = False
        self._lock = threading.Lock()  # Für die Synchronisation der Takt-Ticks

    def _step_callback(self,time, event, seq, data):
        # Increment current step
        self._cur_step = (self._cur_step + 1) % self._steps

        # Set new start_time if there was a step overrun
        if self._cur_step == 0:
            self._start_time = self._start_time + int(self._seconds_per_beat*1000*(self._steps))
            # Calculate new note times
            self.update()
        
        # Set new beat callback
        self._seq.timer(self._start_time + int(self._seconds_per_beat*1000*(self._cur_step+1)), dest=self._step_callback_id)

        print(f"Beat {self._cur_step} ausgelöst: time={time}")

    def add_channel(self, channel):
        """Fügt dem Step-Sequencer einen Kanal hinzu."""
        self._channels.append(channel)

    def remove_channel(self, channel):
        """Entfernt einen Kanal aus dem Step-Sequencer."""
        self._channels.remove(channel)

    def update(self):
        """Lädt die Noten der Step-Kanäle in die Sequenz"""
        print(f"note_update:")
        for channel in self._channels:
            channel_steps = channel.get_steps()
            i = 0
            for step in channel_steps:
                if step:
                    start_tick = self._start_time + int(self._seconds_per_beat*1000*i)  # Berechnet den Startzeitpunkt des Steps
                    note = step[0]                              # MIDI-Notenwert
                    velocity = step[1]                          # Anschlagsstärke

                    # Note-On-Event setzen
                    self._seq.note_on(
                        start_tick,            # Zeitpunkt des Note-On-Ereignisses
                        0,                     # MIDI-Kanal (hier Kanal 0, kann angepasst werden)
                        note,                  # MIDI-Notenwert
                        velocity,              # Anschlagsstärke
                        dest=self._synth_id    # Ziel-Synthesizer-ID
                    )

                    # Note-Off-Event setzen (ein Beat später)
                    stop_tick = self._start_time + int(self._seconds_per_beat*1000*(i+1))  # Berechnet den Startzeitpunkt des Steps
                    self._seq.note_off(
                        stop_tick,             # Zeitpunkt des Note-Off-Ereignisses
                        0,                     # MIDI-Kanal
                        note,                  # MIDI-Notenwert
                        80,                    # Velocity beim Loslassen der Note
                        dest=self._synth_id    # Ziel-Synthesizer-ID
                    )
                    print(f"  note_on({start_tick}, 0, {note}, 100), note_off({stop_tick} , 0, 80, 100)")
                i = i + 1
    
    def play(self):
        self._is_playing = True
        self._start_time = self._seq.get_tick()
        self._cur_step = 0
        self.update()
        self._seq.timer(self._seq.get_tick() + int(self._seconds_per_beat*1000), dest=self._step_callback_id)

    def stop(self):
        self._is_playing = False

class Project:
    """Das Projekt, das die Taktlogik verwaltet und Kanäle steuert."""
    
    def __init__(self, bpm=120, beats_per_measure=4):
        self._instrument_registry = InstrumentRegistry(self)  # Verweis auf die InstrumentRegistry
        self._bpm = bpm
        self._beats_per_measure = beats_per_measure
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

    def get_beats_per_measure(self):
        """Gibt die Ticks pro Takt des Projekts zurück."""
        return self._beats_per_measure

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
                for tick in range(self._beats_per_measure):
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

# Projekt mit BPM=120 und 4 Takte pro Maß
project = Project(bpm=120, beats_per_measure=4)

# Instrumente registrieren
project.get_instrument_registry().register_instrument("Piano", "sf2/GeneralUser-GS.sf2", 0, 0)
project.get_instrument_registry().register_instrument("Jazz Guitar", "sf2/GeneralUser-GS.sf2", 0, 26)
project.get_instrument_registry().register_instrument("Metronome", "sf2/GeneralUser-GS.sf2", 0, 115)

# Step-Sequencer erstellen
step_sequencer = StepSequencer(project.get_instrument_registry().get_synth(), project.get_bpm(), 32, project.get_beats_per_measure())

# Step-Kanal erstellen
step_channel_1 = StepChannel(step_sequencer, "Jazz Guitar")
step_channel_1.set_step( 0,60,127)
step_channel_1.set_step( 1,61,127)
step_channel_1.set_step( 2,62,127)
step_channel_1.set_step( 3,63,127)
step_channel_1.set_step( 4,64,127)
step_channel_1.set_step( 5,63,127)
step_channel_1.set_step( 6,62,127)
step_channel_1.set_step( 7,61,127)
step_channel_1.set_step( 8,60,127)
step_channel_1.set_step( 9,61,127)
step_channel_1.set_step(10,62,127)
step_channel_1.set_step(11,63,127)
step_channel_1.set_step(12,64,127)
step_channel_1.set_step(13,63,127)
step_channel_1.set_step(14,62,127)
step_channel_1.set_step(15,61,127)
step_channel_1.set_step(16,60,127)
step_channel_1.set_step(17,61,127)
step_channel_1.set_step(18,62,127)
step_channel_1.set_step(19,63,127)
step_channel_1.set_step(20,64,127)
step_channel_1.set_step(21,63,127)
step_channel_1.set_step(22,62,127)
step_channel_1.set_step(23,61,127)
step_channel_1.set_step(24,60,127)
step_channel_1.set_step(25,61,127)
step_channel_1.set_step(26,62,127)
step_channel_1.set_step(27,63,127)
step_channel_1.set_step(28,64,127)
step_channel_1.set_step(29,63,127)
step_channel_1.set_step(30,62,127)
step_channel_1.set_step(31,61,127)

# Step-Kanäle zuweisen
step_sequencer.add_channel(step_channel_1)

# Instrument-Kanäle erstellen
for port_name in mido.get_input_names():
    fluid_midi_channel = FreeMidiChannel(project, port_name, "Piano")
    project.add_channel(fluid_midi_channel)

metronome_channel = FreeMetronomeChannel(project, "Metronome")
project.add_channel(metronome_channel)

step_sequencer_channel = StepSequencerChannel(project, step_sequencer)
project.add_channel(step_sequencer_channel)

# Starte das Projekt
project.play()

# Stoppe nach einer Weile (5 Sekunden) das Projekt
time.sleep(20)
project.stop()

# TODO
# - Richtiger Step-Channel MIDI-Kanal
# - Lautstärke Step-Channel MIDI-Kanal
# - Polyphoner Step-Channel MIDI-Kanal
# - Coole Anzeige
# - Funktionierender Stopp
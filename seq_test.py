import fluidsynth
import time
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

# Initialisiere FluidSynth
fs = fluidsynth.Synth()
fs.start(driver=DRIVER)

# Lade ein SoundFont (z.B. GeneralUser SoundFont)
soundfont = "sf2/GeneralUser-GS.sf2"
sfid = fs.sfload(soundfont)
fs.program_select(0, sfid, 0, 0)

# Initialisiere den Sequencer
seq = fluidsynth.Sequencer()

# Registriere den Synthesizer beim Sequencer
synth_id = seq.register_fluidsynth(fs)

# Setze die BPM (Beats pro Minute)
bpm = 120
ticks_per_beat = 480
step_duration = int((60 / bpm) * ticks_per_beat / 4)  # 4 Schritte pro Schlag (16tel-Noten)

# Teste eine Callback-Funktion
def seq_callback(time, event, seq, data):
    print(f"Callback ausgelöst: time={time}, event={event}, data={data}")

# Registriere das Callback im Sequencer
callback_id = seq.register_client("myCallback", seq_callback)

# Planen und Testen
try:
    print(f"Testing Synthesizer directly (at {seq.get_tick()})...")
    fs.noteon(0, 60, 100)  # Note C4 anspielen
    time.sleep(1)
    fs.noteoff(0, 60)      # Note C4 stoppen

    # Feste Startzeit für die Sequenz
    initial_start_time = seq.get_tick()

    print(f"Adding scheduled events (at {seq.get_tick()})...")
    seq.note_on(seq.get_tick() + 500, 0, 60, 100, dest=synth_id)
    seq.note_off(seq.get_tick() + 1000, 0, 60, 80, dest=synth_id)

    print(f"Adding timer events (at {seq.get_tick()})...")
    seq.timer(seq.get_tick() + 1500, dest=callback_id)

    print(f"Waiting for scheduled events (at {seq.get_tick()})...")
    time.sleep(5)
    print(f"Stopping at {seq.get_tick()}...")
    
except KeyboardInterrupt:
    print("Sequencer gestoppt.")
finally:
    fs.delete()

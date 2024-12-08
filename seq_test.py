import fluidsynth
import time

# Initialisiere FluidSynth
fs = fluidsynth.Synth()
fs.start()

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
# Berechne die Dauer eines Schritts in Ticks (hier gehen wir von 480 Ticks pro Schlag aus)
ticks_per_beat = 480
step_duration = (60 / bpm) * ticks_per_beat / 4  # 4 Schritte pro Schlag (16tel-Noten)

# 32 Schritte (also ein Pattern mit 32 Schritten)
num_steps = 32
note_on_velocity = 80  # Lautstärke der Note
note_off_velocity = 0  # Lautstärke zum Stoppen der Note

# Beispiel für ein 32-Schritte-Pattern (z.B. eine einfache Melodie)
pattern = [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83, 84, 86,
           88, 90, 91, 93, 95, 96, 98, 100, 102, 104, 105, 107, 109, 111, 112, 114]

# Funktion, um die 32 Schritte zu laden
def load_sequence(start_time):
    for step in range(num_steps):
        note = pattern[step]
        seq.note_on(int(start_time + step * step_duration), 0, note, note_on_velocity, dest=synth_id)  # Note einschalten
        seq.note_off(int(start_time + (step + 1) * step_duration), 0, note, note_off_velocity, dest=synth_id)  # Note ausschalten

def seq_callback(time, event, seq, data):
    print('callback called!')

# Setze den Sequencer so, dass er die Sequenz wiederholt
try:
    print("Starting sequencer...")
    
    # Feste Startzeit für die Sequenz
    initial_start_time = seq.get_tick()  # Die Startzeit in Ticks (relativ zu einem Referenzzeitpunkt)

    callback_id = seq.register_client("myCallback", seq_callback)

    seq.timer(initial_start_time, dest=callback_id)

    seq.note_on(initial_start_time + 500, 0, 60, 80, dest=synth_id)

    time.sleep(5)
except KeyboardInterrupt:
    print("Sequencer gestoppt.")

#!/usr/bin/env python3

import os
import sys
import time
import queue
import numpy as np
import sounddevice as sd

try:
    from dotenv import load_dotenv
    adk_env = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(adk_env):
        load_dotenv(adk_env)
except Exception:
    pass
SAMPLE_RATE = int(os.getenv("SD_SAMPLE_RATE", "16000"))
BLOCK_SIZE = int(os.getenv("SD_BLOCK_SIZE", "1600"))
RMS_THRESHOLD = float(os.getenv("VAD_RMS_THRESHOLD", "0.005"))
MIN_SPEECH_MS = int(os.getenv("VAD_MIN_SPEECH_MS", "400"))
END_SILENCE_MS = int(os.getenv("VAD_END_SILENCE_MS", "600"))
MAX_SPEECH_MS = int(os.getenv("VAD_MAX_SPEECH_MS", "10000"))

def rms_energy(block: np.ndarray) -> float:
    if block.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(block))))

def transcribe(audio: np.ndarray, model) -> str:
    result = model.transcribe(audio, language="en")
    return (result.get("text") or "").strip()

def main():
    print("[console_runner] Starting microphone")
    sys.stdout.flush()

    dev_env = os.getenv("SD_DEFAULT_DEVICE")
    if dev_env:
        try:
            idx = int(dev_env)
            sd.default.device = (idx, None)
            print(f"[console_runner] Using input device index {idx}")
        except Exception:
            print(f"[console_runner] Invalid device '{dev_env}', using default")

    import whisper
    model_name = os.getenv("WHISPER_MODEL", "base")
    print(f"[console_runner] Loading Whisper model: {model_name}")
    sys.stdout.flush()
    model = whisper.load_model(model_name)
    print("[console_runner] Whisper ready. Listening")
    sys.stdout.flush()

    q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=50)

    def callback(indata, frames, time_info, status):
        if status:
            pass
        q.put(indata.copy().astype(np.float32).flatten())

    frame_ms = int(1000 * BLOCK_SIZE / SAMPLE_RATE)
    in_speech = False
    collected: list[np.ndarray] = []
    collected_ms = 0
    silence_ms = 0

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=BLOCK_SIZE,
            callback=callback,
        ):
            while True:
                block = q.get()
                e = rms_energy(block)

                if not in_speech:
                    if e >= RMS_THRESHOLD:
                        in_speech = True
                        collected = [block]
                        collected_ms = frame_ms
                        silence_ms = 0
                    else:
                        continue
                else:
                    collected.append(block)
                    collected_ms += frame_ms
                    if e < RMS_THRESHOLD:
                        silence_ms += frame_ms
                    else:
                        silence_ms = 0

                    should_finalize = (
                        (collected_ms >= MIN_SPEECH_MS and silence_ms >= END_SILENCE_MS)
                        or (collected_ms >= MAX_SPEECH_MS)
                    )

                    if should_finalize:
                        segment = np.concatenate(collected, axis=0)
                        in_speech = False
                        collected = []
                        collected_ms = 0
                        silence_ms = 0

                        try:
                            text = transcribe(segment, model)
                        except Exception as tr_e:
                            print(f"[console_runner] Transcribe error: {tr_e}")
                            sys.stdout.flush()
                            continue

                        if not text:
                            continue

                        print(f"Detected: '{text}'")
                        sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n[console_runner] Exiting")
    except Exception as e:
        print(f"[console_runner] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

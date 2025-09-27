#!/usr/bin/env python3
import os
import sys
import time
import queue
import requests
import json
 

try:
	from dotenv import load_dotenv  
	adk_env = os.path.join(os.path.dirname(__file__), '..', '.env')
	if os.path.exists(adk_env):
		load_dotenv(adk_env)
except Exception:
	pass

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
	print("[console_runner] GOOGLE_API_KEY not set. Put it in ADK/.env or export it in the shell.")
	sys.exit(1)

try:
	from google import genai
	client = genai.Client(api_key=GOOGLE_API_KEY)
	MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
except Exception as e:
	print(f"[console_runner] Failed to init genai client: {e}")
	sys.exit(1)

import numpy as np
import sounddevice as sd


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


def send_voice_data_to_frontend(voice_data: dict):
	"""Send voice data to the frontend via HTTP request"""
	try:
		# Try to send to the frontend if it's running
		# The frontend will need to expose an HTTP endpoint for this
		response = requests.post(
			"http://localhost:3000/api/voice-data",
			json=voice_data,
			timeout=0.1  # Very short timeout to avoid blocking
		)
		if response.status_code == 200:
			print(f"[console_runner] Voice data sent to frontend: {voice_data}")
	except requests.exceptions.RequestException:
		# Frontend not running or endpoint not available, continue silently
		pass


def send_voice_status_to_frontend(status: dict):
	"""Send voice status to the frontend via HTTP request"""
	try:
		response = requests.post(
			"http://localhost:3000/api/voice-status",
			json=status,
			timeout=0.1  # Very short timeout to avoid blocking
		)
		if response.status_code == 200:
			print(f"[console_runner] Voice status sent to frontend: {status}")
	except requests.exceptions.RequestException:
		# Frontend not running or endpoint not available, continue silently
		pass


def main():

	print("Say 'Gemini' to activate, then speak your command. Ctrl+C to stop.\n")

	dev_env = os.getenv("SD_DEFAULT_DEVICE")
	if dev_env:
		try:
			idx = int(dev_env)
			sd.default.device = (idx, None)
			print(f"[console_runner] Using input device index {idx}")
		except Exception:
			print(f"[console_runner] Invalid SD_DEFAULT_DEVICE='{dev_env}', using system default")

	import whisper
	model_name = os.getenv("WHISPER_MODEL", "base")
	print(f"[console_runner] Loading Whisper model: {model_name} ...")
	model = whisper.load_model(model_name)
	print("[console_runner] Whisper ready.")

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
	
	WAKE_WORD = "gemini"
	waiting_for_wake_word = True
	activated = False

	try:
		with sd.InputStream(
			samplerate=SAMPLE_RATE,
			channels=1,
			dtype="float32",
			blocksize=BLOCK_SIZE,
			callback=callback,
		):
			print("[console_runner] Listening for 'Gemini'...")
			while True:
				block = q.get()
				e = rms_energy(block)
				
				
				if not in_speech:
					if e >= RMS_THRESHOLD:
						# start speech
						in_speech = True
						collected = [block]
						collected_ms = frame_ms
						silence_ms = 0
					else:
						# still idle
						continue
				else:
					# already in speech
					collected.append(block)
					collected_ms += frame_ms
					if e < RMS_THRESHOLD:
						silence_ms += frame_ms
					else:
						silence_ms = 0

					# finalize if silence long enough or max length reached
					if (collected_ms >= MIN_SPEECH_MS and silence_ms >= END_SILENCE_MS) or collected_ms >= MAX_SPEECH_MS:
						segment = np.concatenate(collected, axis=0)
						in_speech = False
						collected = []
						collected_ms = 0
						silence_ms = 0

						text = transcribe(segment, model)
						if not text:
							print("[console_runner] (no speech)")
							continue
						
						det = text.lower().strip()
						print(f"Detected: '{det}'")
						
						# Send voice data to frontend
						voice_data = {
							"text": text,
							"normalized_text": det,
							"timestamp": time.time(),
							"status": "detected"
						}
						send_voice_data_to_frontend(voice_data)
						
						if waiting_for_wake_word:
							det_clean = det.replace(" ", "").replace(",", "").replace(".", "").lower()
							# exact or partial match
							wake_word_found = (WAKE_WORD in det_clean or 
											   WAKE_WORD in det or 
											   det.startswith(WAKE_WORD) or
											   WAKE_WORD in det.replace(" ", ""))
							
							if wake_word_found:
								print("[console_runner] Activated! Listening for command...")
								waiting_for_wake_word = False
								activated = True
								
								# Send activation status to frontend
								status_data = {
									"status": "activated",
									"message": "Listening for command...",
									"timestamp": time.time()
								}
								send_voice_status_to_frontend(status_data)
							else:
								continue
						else:

							try:
								gen_config = {
									"temperature": float(os.getenv("GEN_TEMPERATURE", "0.4")),
									"top_p": float(os.getenv("GEN_TOP_P", "0.9")),
									"max_output_tokens": int(os.getenv("GEN_MAX_TOKENS", "256")),
								}
								prompt_text = (
									"You are a concise, helpful assistant. Prefer short, direct answers. "
									"If action items are requested, reply with clear bullet points.\n\n"
									f"User said: {text}\nRespond helpfully."
								)
								contents = [
									{"role": "user", "parts": [{"text": prompt_text}]}
								]
								try:
									resp = client.models.generate_content(
										model=MODEL,
										contents=contents,
										generation_config=gen_config,
									)
								except TypeError:
									resp = client.models.generate_content(
										model=MODEL,
										contents=contents,
									)
								out = "".join(part.text for cand in getattr(resp, 'candidates', []) for part in getattr(getattr(cand, 'content', None), 'parts', []) if hasattr(part, 'text'))
								spoken = out or '[no text response]'
								print(f"Gemini: {spoken}\n")
								
								# Send response data to frontend
								response_data = {
									"text": text,
									"response": spoken,
									"timestamp": time.time(),
									"status": "response"
								}
								send_voice_data_to_frontend(response_data)
								
								print("[console_runner] Listening for 'Gemini'...")
								waiting_for_wake_word = True
								activated = False
								
								# Send status back to listening
								status_data = {
									"status": "listening",
									"message": "Listening for 'Gemini'...",
									"timestamp": time.time()
								}
								send_voice_status_to_frontend(status_data)
							except Exception as e:
								print(f"[console_runner] GenAI error: {e}")
								print("[console_runner] Listening for 'Gemini'...")
								waiting_for_wake_word = True
								activated = False
								
								# Send error status to frontend
								error_data = {
									"status": "error",
									"message": f"GenAI error: {e}",
									"timestamp": time.time()
								}
								send_voice_status_to_frontend(error_data)

	except KeyboardInterrupt:
		print("\n[console_runner] Exiting...")

if __name__ == '__main__':
	main()

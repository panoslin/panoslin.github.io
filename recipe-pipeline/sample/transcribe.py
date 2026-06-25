import json, os, sys
from faster_whisper import WhisperModel

model_size = os.environ.get("ASR_MODEL", "medium")
print(f"loading model: {model_size}", flush=True)
model = WhisperModel(model_size, device="cpu", compute_type="int8")

segments, info = model.transcribe(
    "sample/audio.wav",
    language="zh",
    vad_filter=True,
    beam_size=5,
    initial_prompt="这是一个中文美食食谱视频，主播会口播食材和具体用量，例如克、毫升、勺、个、适量。",
)
print(f"lang={info.language} dur={info.duration:.1f}s", flush=True)
out = []
for s in segments:
    line = f"[{s.start:5.1f}-{s.end:5.1f}] {s.text.strip()}"
    print(line, flush=True)
    out.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
json.dump(out, open("sample/transcript.json", "w"), ensure_ascii=False, indent=2)
print(f"\nSAVED sample/transcript.json segments={len(out)}", flush=True)


import cv2
import numpy as np
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()

video = filedialog.askopenfilename(
    title="Select Original CCTV Video",
    filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")]
)

if not video:
    print("No video selected")
    exit()

folder = filedialog.askdirectory(
    title="Select Output Folder"
)

if not folder:
    print("No output folder selected")
    exit()

cap = cv2.VideoCapture(video)

total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

if not cap.isOpened() or total < 30:
    print("Unable to open video or fewer than 30 frames")
    cap.release()
    exit()

out = Path(folder) / "EagleVision_Video_1_CLEAN"
out.mkdir(parents=True, exist_ok=True)

indices = np.linspace(0, total - 1, 30, dtype=int)

for i, idx in enumerate(indices, start=1):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
    ret, frame = cap.read()

    if not ret:
        print("Failed to read frame:", idx)
        continue

    name = out / f"video_1_frame_{i:03d}.jpg"

    cv2.imwrite(
        str(name),
        frame,
        [cv2.IMWRITE_JPEG_QUALITY, 98]
    )

cap.release()

print("Extraction completed!")
print("Frames saved:", out)
print("Total requested: 30")

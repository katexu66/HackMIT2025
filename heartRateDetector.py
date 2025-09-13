import cv2
import numpy as np
import scipy.signal
import time

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

cap = cv2.VideoCapture(0)

greenValues = []
timeStamps = []

start_time = time.time()
duration = 15

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))

    for (x,y,w,h) in faces:
        forehead_x = x
        forehead_y = y
        forehead_w = w
        forehead_h = int(h*0.3)

        roi = frame[forehead_y:forehead_y + forehead_h, forehead_x:forehead_x + forehead_w]
        if roi.size == 0:
            continue

        cv2.rectangle(frame, (forehead_x, forehead_y), (forehead_x + forehead_w, forehead_y + forehead_h), (0, 255, 0), 2)

        avg_green = np.mean(roi[:, :, 1])
        greenValues.append(avg_green)
        timeStamps.append(time.time() - start_time)

    cv2.imshow('Forehead isolation', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

greenValues = np.array(greenValues)
timeStamps = np.array(timeStamps)

fps = len(greenValues) / duration
resampled_times = np.linspace(timeStamps[0], timeStamps[-1], len(greenValues))
resampled_signal = np.interp(resampled_times, timeStamps, greenValues)

lowcut = 0.7
highcut = 4.0

nyquist = 0.5*fps
low = lowcut/nyquist
high = highcut/nyquist

if high >= 1:
    high = 0.99
if low <= 0:
    low = 0.01

b, a = scipy.signal.butter(3, [low, high], btype='band')
filtered = scipy.signal.filtfilt(b, a, resampled_signal)

fft = np.abs(np.fft.rfft(filtered))
freqs = np.fft.rfftfreq(len(filtered), 1/fps)

peak_freq = freqs[np.argmax(fft)]
bpm = peak_freq*60
print(f"\n Estimated Heart Rate: {bpm:.2f} BPM")

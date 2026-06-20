from ultralytics import YOLO
import cv2

model = YOLO(r"E:\traffic_ai\Backend\detectors\models\seatbelt.pt")

img = cv2.imread(r"E:\traffic_ai\Backend\debug_api_input.jpg")

results = model(
    img,
    conf=0.01,
    save=True
)

print("BOXES:", len(results[0].boxes))

for b in results[0].boxes:
    print(
        model.names[int(b.cls[0])],
        float(b.conf[0])
    )
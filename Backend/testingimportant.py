from ultralytics import YOLO
import cv2

model = YOLO(r"E:\traffic_ai\Backend\detectors\models\helmet.pt")

img = cv2.imread(r"E:\Downloads\50 photos\pexels-khoa-le-1920596591-31180327.jpg")

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
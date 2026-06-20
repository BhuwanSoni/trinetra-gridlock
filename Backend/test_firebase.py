from firebase.storage import upload_image
import os

local_file = r"E:\traffic_ai\Backend\evidence\images\0A4A9AE6_20260620_053328_full.jpg"

url = upload_image(
    local_file,
    f"evidence/full/{os.path.basename(local_file)}"
)

print(url)
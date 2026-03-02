import cv2
import urllib.parse

# Read QR code image
img = cv2.imread("mfacode.png")

# Decode QR
detector = cv2.QRCodeDetector()
data, _, _ = detector.detectAndDecode(img)

if data:
    print("Full QR data:", data)
    # Extract secret key
    secret = urllib.parse.parse_qs(data.split("?")[1])["secret"][0]
    print(f"Your Secret Key: {secret}")
else:
    print("No QR code found - make sure image is clear and cropped properly")
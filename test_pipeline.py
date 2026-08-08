import sys

sys.path.insert(0, ".")
import cv2

from core.recommender import HairstyleRecommender

rec = HairstyleRecommender()
result = rec.analyze("data/foto_test.jpeg")

if result["success"]:
    print("=" * 40)
    print("Bentuk wajah :", result["label"])
    print("Confidence   :", f"{result['confidence'] * 100:.1f}%")
    print("Alasan       :", result["reasoning"])
    print()
    print("Fitur geometri:")
    for k, v in result["features"].items():
        print(f"  {k:20s}: {v}")
    print()
    print("Rekomendasi hairstyle:")
    for i, h in enumerate(result["hairstyles"], 1):
        print(f"  {i}. {h['name']} - {h['description'][:50]}...")
    print("=" * 40)

    cv2.imwrite("data/hasil_annotasi.jpg", result["annotated_img"])
    print("Foto annotasi disimpan ke data/hasil_annotasi.jpg")
else:
    print("ERROR:", result["error"])

import io
import uuid

from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app


def make_image_bytes() -> bytes:
    img = Image.new("RGB", (256, 256), (210, 170, 150))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def run():
    client = TestClient(app)
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "gender": "Female",
            "city": "Lahore",
        },
    )
    print("register:", reg.status_code)
    token = reg.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    print("me:", me.status_code)

    image_bytes = make_image_bytes()
    selfie = client.post(
        "/api/v1/profile/selfie",
        headers=headers,
        files={"file": ("selfie.jpg", image_bytes, "image/jpeg")},
    )
    print("selfie:", selfie.status_code)

    body = client.post(
        "/api/v1/profile/body",
        headers=headers,
        files={"file": ("body.jpg", image_bytes, "image/jpeg")},
    )
    print("body:", body.status_code)

    ward1 = client.post(
        "/api/v1/wardrobe/upload",
        headers=headers,
        files={"file": ("kurta_blue.jpg", image_bytes, "image/jpeg")},
        data={"fabric_weight": "medium", "occasion_tags": "[\"Casual\",\"Formal\"]"},
    )
    print("wardrobe1:", ward1.status_code, ward1.json().get("category"))

    ward2 = client.post(
        "/api/v1/wardrobe/upload",
        headers=headers,
        files={"file": ("salwar_white.jpg", image_bytes, "image/jpeg")},
        data={"fabric_weight": "light", "occasion_tags": "[\"Casual\"]"},
    )
    print("wardrobe2:", ward2.status_code, ward2.json().get("category"))

    rec = client.post(
        "/api/v1/recommend/daily",
        headers=headers,
        json={"occasion": "Casual", "style_pref": "Eastern"},
    )
    print("recommend:", rec.status_code)
    if rec.status_code == 200:
        payload = rec.json()
        print("recommend score:", payload.get("score"))
        print("recommend has why:", bool(payload.get("why_this_suits_you")))
        print("recommend has weather:", isinstance(payload.get("weather"), dict))
    else:
        print(rec.text)

    palette = client.get("/api/v1/profile/color-palette", headers=headers)
    print("palette:", palette.status_code)

    combo_id = ward1.json().get("id")
    combo = client.get(
        f"/api/v1/combo/{combo_id}?occasion=Casual&style_pref=Eastern",
        headers=headers,
    )
    print("combo:", combo.status_code)
    if combo.status_code == 200:
        print("combo total:", combo.json().get("total_combos"))
    else:
        print(combo.text)


if __name__ == "__main__":
    run()

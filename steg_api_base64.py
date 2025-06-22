from fastapi import FastAPI, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
from io import BytesIO
from PIL import Image
import base64

app = FastAPI()

# ✅ السماح للفرونت بالتواصل
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # غيّريها حسب موقع الويب لو حبيتي
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 تشفير - encode
@app.post("/encode")
async def encode(image: UploadFile = File(...), message: Optional[str] = Form(None), hidden_image: Optional[UploadFile] = File(None)):
    try:
        image_data = await image.read()
        img = Image.open(BytesIO(image_data)).convert("RGB")

        if message:
            # Encode message into image
            message += chr(0)
            bits = ''.join(format(ord(c), '08b') for c in message)

            encoded = img.copy()
            pixels = list(encoded.getdata())
            new_pixels = []

            bit_index = 0
            for pixel in pixels:
                if bit_index < len(bits):
                    r, g, b = pixel
                    r = (r & ~1) | int(bits[bit_index])
                    bit_index += 1
                    new_pixels.append((r, g, b))
                else:
                    new_pixels.append(pixel)

            encoded.putdata(new_pixels)

        elif hidden_image:
            # Embed another image into the main image
            hidden_data = await hidden_image.read()
            hidden = Image.open(BytesIO(hidden_data)).resize(img.size).convert("RGB")

            encoded = Image.new("RGB", img.size)
            pixels = []
            for p1, p2 in zip(img.getdata(), hidden.getdata()):
                new_pixel = tuple((a & 0xF0) | (b >> 4) for a, b in zip(p1, p2))
                pixels.append(new_pixel)
            encoded.putdata(pixels)

        else:
            return JSONResponse(status_code=400, content={"error": "No message or hidden image provided."})

        buffer = BytesIO()
        encoded.save(buffer, format="PNG")
        base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {"image": base64_image}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# 🕵️‍♀️ فك التشفير - decode
@app.post("/decode")
async def decode(image: UploadFile):
    try:
        image_data = await image.read()
        img = Image.open(BytesIO(image_data)).convert("RGB")
        pixels = list(img.getdata())

        # Try extract message
        bits = ""
        for pixel in pixels:
            r = pixel[0]
            bits += str(r & 1)

        chars = []
        for i in range(0, len(bits), 8):
            byte = bits[i:i+8]
            if len(byte) < 8:
                continue
            char = chr(int(byte, 2))
            if char == chr(0):
                break
            chars.append(char)

        message = ''.join(chars)

        if message:
            return {"message": message}

        # Try extract image
        extracted = Image.new("RGB", img.size)
        hidden_pixels = []
        for pixel in pixels:
            r, g, b = pixel
            new_pixel = ((r & 0x0F) << 4, (g & 0x0F) << 4, (b & 0x0F) << 4)
            hidden_pixels.append(new_pixel)
        extracted.putdata(hidden_pixels)

        buffer = BytesIO()
        extracted.save(buffer, format="PNG")
        hidden_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {"hidden_image": hidden_base64}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

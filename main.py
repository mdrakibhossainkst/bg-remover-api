from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response
from rembg import remove
from PIL import Image
import io

# অ্যাপ তৈরি করছি
app = FastAPI()

# হোম পেজ (টেস্ট করার জন্য)
@app.get("/")
def home():
    return {"message": "BG Remover API is running!", "status": "active"}

# হেলথ চেক (সার্ভার বাঁচিয়ে রাখার জন্য)
@app.get("/health")
def health():
    return {"status": "ok"}

# মূল ব্যাকগ্রাউন্ড রিমুভ API
@app.post("/remove-bg")
async def remove_background(file: UploadFile = File(...)):
    # ব্যবহারকারীর পাঠানো ছবি পড়ি
    input_image = Image.open(io.BytesIO(await file.read()))
    
    # ব্যাকগ্রাউন্ড রিমুভ করি (এটাই ম্যাজিক!)
    output_image = remove(input_image)
    
    # রেজাল্ট ফিরিয়ে দিই
    img_byte_arr = io.BytesIO()
    output_image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    
    return Response(content=img_byte_arr, media_type="image/png")

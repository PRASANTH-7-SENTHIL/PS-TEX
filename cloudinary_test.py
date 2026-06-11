import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils

# Load variables from .env
load_dotenv()

# 1. Configure Cloudinary from environment
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

def run_cloudinary_flow():
    # 2. Upload a sample image URL from Cloudinary's demo domains
    sample_image_url = "https://res.cloudinary.com/demo/image/upload/dog.jpg"
    print("Uploading sample image to Cloudinary...")
    upload_result = cloudinary.uploader.upload(sample_image_url)
    
    secure_url = upload_result.get("secure_url")
    public_id = upload_result.get("public_id")
    print(f"Secure URL: {secure_url}")
    print(f"Public ID: {public_id}")
    
    # 3. Get image details (metadata: width, height, format, bytes)
    print("\nFetching image metadata...")
    image_details = cloudinary.api.resource(public_id)
    
    width = image_details.get("width")
    height = image_details.get("height")
    img_format = image_details.get("format")
    bytes_size = image_details.get("bytes")
    
    print(f"Width: {width}px")
    print(f"Height: {height}px")
    print(f"Format: {img_format}")
    print(f"File Size: {bytes_size} bytes")
    
    # 4. Transform the image using f_auto and q_auto
    # f_auto: Automatically delivers the image in the most optimal format (webp, avif, png, etc.) supported by the user's browser.
    # q_auto: Automatically optimizes the quality of the image to minimize file size while maintaining visual quality.
    transformed_url = cloudinary.utils.cloudinary_url(
        public_id,
        fetch_format="auto",
        quality="auto",
        secure=True
    )[0]
    
    print("\nDone! Click link below to see optimized version of the image. Check the size and the format.")
    print(transformed_url)

if __name__ == "__main__":
    run_cloudinary_flow()

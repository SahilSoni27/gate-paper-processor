import os
from dotenv import load_dotenv
import cloudinary

# Load environment variables from .env
load_dotenv()

# Configure Cloudinary using env variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

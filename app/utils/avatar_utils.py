import os
from pathlib import Path
from flask import current_app
from PIL import Image
import io
import base64

def get_default_avatar():
    """Returns the default avatar as binary data"""
    # Create a simple default avatar (white circle on blue background)
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (200, 200), color='#1976d2')
    draw = ImageDraw.Draw(img)
    draw.ellipse((20, 20, 180, 180), fill='#ffffff')
    
    # Save to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

def process_avatar(file_storage):
    """Process uploaded avatar image"""
    try:
        # Open the image
        img = Image.open(file_storage)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        
        # Resize image to 200x200 pixels
        img.thumbnail((200, 200))
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except Exception as e:
        current_app.logger.error(f"Error processing avatar: {str(e)}")
        return None

def avatar_to_base64(avatar_data):
    """Convert binary avatar data to base64 string"""
    if not avatar_data:
        return None
    return f"data:image/png;base64,{base64.b64encode(avatar_data).decode('utf-8')}"

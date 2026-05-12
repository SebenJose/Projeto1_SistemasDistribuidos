import os
from PIL import Image, ImageDraw, ImageFont

objects = ["Cachorro", "Carro", "Maca", "Bicicleta", "Computador", "Violao", "Livro", "Relogio", "Aviao", "Cadeira"]

os.makedirs("objects_images", exist_ok=True)

# Try to use a basic font, or default
try:
    font = ImageFont.truetype("arial.ttf", 40)
except IOError:
    font = ImageFont.load_default()

for obj in objects:
    # Create an image with solid color
    img = Image.new('RGB', (400, 400), color = (73, 109, 137))
    d = ImageDraw.Draw(img)
    
    # Text
    text = obj
    
    # Try to calculate text size for centering
    try:
        text_bbox = d.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
    except AttributeError:
        # Fallback for older PIL versions
        text_width, text_height = d.textsize(text, font=font)
        
    x = (400 - text_width) / 2
    y = (400 - text_height) / 2
    
    d.text((x, y), text, font=font, fill=(255, 255, 0))
    
    # Save the image
    img.save(f"objects_images/{obj}.png")

print("Imagens geradas com sucesso em objects_images/")

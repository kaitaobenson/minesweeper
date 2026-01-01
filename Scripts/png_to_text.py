from pathlib import Path
from PIL import Image
from math import *

def get_image_as_txt(image: Image) -> str:
    width, height = image.size
    pixel_values = image.load()

    bytes_per_row = ceil(width/8)

    lines = []
    for y in range(height):
        row = []
        for i in range(bytes_per_row):
            bits = ""
            for j in range(8):
                x = i * 8 + j
                if x >= width:
                    bits += "0"
                else:
                    r, g, b, a = pixel_values[x, y]
                    is_black = r == 0 and g == 0 and b == 0 and a == 255
                    bits += "1" if is_black else "0"
                
            row.append("0b" + bits)
        lines.append("\t" + ", ".join(row))

    txt = (
        f"({width}, {height}, bytes([\n" 
        + ",\n".join(lines)
        + "\n]))"
    )

    return txt

def get_spritesheet_as_txt(image: Image, width: int, height: int) -> str:
    x_amount = floor(image.width / width)
    y_amount = floor(image.height / height)

    if x_amount == 0 or y_amount == 0:
        return ""
    
    sprites_as_txt: list = []

    for y in range(y_amount):
        for x in range(x_amount):
            cropped = image.crop((x * width, y * height, (x+1) * width, (y+1) * height))
            txt = get_image_as_txt(cropped)
            sprites_as_txt.append(txt)
    
    spritesheet_as_txt = (
        "["
        + ",\n".join(sprites_as_txt)
        + "]"
    )
    return spritesheet_as_txt

#PATH = "Minesweeper/Assets/Sprites/Numbers"
#txt = get_spritesheet_as_txt(PATH + "/numbers.png", 6, 9)
#Path(PATH + "/numbers.txt").write_text(txt)

path1 = Path("Minesweeper/Assets/Sprites/Menu")
for file in Path(path1).iterdir():
    if file.suffix.lower() == ".png":
        txt = get_image_as_txt(Image.open(file))
        txt_file = Path(str(file).removesuffix(".png") + ".txt")
        txt_file.write_text(txt)
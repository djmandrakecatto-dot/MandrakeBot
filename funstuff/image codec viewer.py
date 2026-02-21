from PIL import Image
import math

BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
BASE36 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

def decode_base(s, alphabet):
    base = len(alphabet)
    value = 0
    for char in s:
        value = value * base + alphabet.index(char)
    return value

def decode_image_mixed(encoded_string):
    # Split main parts
    part1, part2, part3, part4 = encoded_string.split("#")

    # Width / Height
    width, height = map(int, part1.split("x"))

    # Encoded blocks
    blocks = part2.strip("|").split("|")

    # Palette
    palette_count = int(part3)
    palette_data = part4

    # Decode palette (base36, fixed 2 chars per channel)
    palette = []
    idx = 0
    for _ in range(palette_count):
        r = decode_base(palette_data[idx:idx+2], BASE36)
        g = decode_base(palette_data[idx+2:idx+4], BASE36)
        b = decode_base(palette_data[idx+4:idx+6], BASE36)
        palette.append((r, g, b))
        idx += 6

    # Decode pixel blocks
    indices = []
    for block_index, block in enumerate(blocks):

        if block_index % 2 == 0:
            combined = decode_base(block, BASE32)
        else:
            combined = decode_base(block, BASE36)

        # Extract 4 indices from 32-bit value
        i1 = (combined >> 24) & 0xFF
        i2 = (combined >> 16) & 0xFF
        i3 = (combined >> 8) & 0xFF
        i4 = combined & 0xFF

        indices.extend([i1, i2, i3, i4])

    # Trim padding
    total_pixels = width * height
    indices = indices[:total_pixels]

    # Rebuild image
    img = Image.new("RGB", (width, height))
    pixels = [palette[i] for i in indices]
    img.putdata(pixels)

    return img


if __name__ == "__main__":
    with open("encoded.txt", "r") as f:
        encoded_data = f.read()

    image = decode_image_mixed(encoded_data)
    image.show()

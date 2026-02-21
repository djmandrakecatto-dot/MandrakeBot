from PIL import Image
import os

BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
BASE36 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

def encode_base(n, alphabet):
    if n == 0:
        return alphabet[0]
    base = len(alphabet)
    digits = ""
    while n:
        digits = alphabet[n % base] + digits
        n //= base
    return digits

def encode_image_mixed(path):
    img = Image.open(path).convert("RGB").quantize(
    colors=256,
    method=Image.MEDIANCUT,
    dither=Image.NONE
    ).convert("RGB")

    width, height = img.size
    pixels = list(img.getdata())

    # 1️⃣ Extract palette
    palette = []
    palette_map = {}

    for p in pixels:
        if p not in palette_map:
            palette_map[p] = len(palette)
            palette.append(p)

    # 2️⃣ Convert pixels → indices
    indices = [palette_map[p] for p in pixels]

    # Pad to multiple of 4
    while len(indices) % 4 != 0:
        indices.append(0)

    encoded_stream = ""
    block_count = 0

    # 3️⃣ Process 4 pixels per block
    for i in range(0, len(indices), 4):
        i1, i2, i3, i4 = indices[i:i+4]
        combined = (i1 << 24) | (i2 << 16) | (i3 << 8) | i4

        if block_count % 2 == 0:
            encoded_stream += encode_base(combined, BASE32)
        else:
            encoded_stream += encode_base(combined, BASE36)

        encoded_stream += "|"
        block_count += 1

    # 4️⃣ Encode palette at end (base36)
    palette_data = ""
    for (r, g, b) in palette:
        palette_data += encode_base(r, BASE36).rjust(2, BASE36[0])
        palette_data += encode_base(g, BASE36).rjust(2, BASE36[0])
        palette_data += encode_base(b, BASE36).rjust(2, BASE36[0])

    final = f"{width}x{height}#{encoded_stream}#{len(palette)}#{palette_data}"
    return final

def save_encoded_image(input_path):
    encoded = encode_image_mixed(input_path)

    output_path = os.path.splitext(input_path)[0] + ".miximg"

    with open(output_path, "w", encoding="ascii") as f:
        f.write(encoded)

    print("Saved to:", output_path)


if __name__ == "__main__":
    save_encoded_image("input.png")

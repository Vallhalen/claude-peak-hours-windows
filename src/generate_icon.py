"""Generate .ico file for the app (run once)."""

from PIL import Image, ImageDraw


def generate_ico(path: str = "assets/icon.ico") -> None:
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        margin = max(1, size // 16)
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=(0, 180, 80, 255),
        )
        images.append(img)

    images[0].save(path, format="ICO", sizes=[(s, s) for s in sizes],
                   append_images=images[1:])
    print(f"Icon saved to {path}")


if __name__ == "__main__":
    generate_ico()

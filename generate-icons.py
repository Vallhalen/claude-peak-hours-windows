"""Generate all PNG icons for PWA and widget."""

from PIL import Image, ImageDraw


def circle_icon(size: int, color: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = max(2, size // 12)
    draw.ellipse([margin, margin, size - margin, size - margin],
                 fill=(*color, 255))
    return img


GREEN = (0, 180, 80)
RED = (220, 50, 50)
YELLOW = (240, 180, 0)

# PWA icons (green default)
circle_icon(192, GREEN).save("icons/icon-192.png")
circle_icon(512, GREEN).save("icons/icon-512.png")

# Widget dot indicators
circle_icon(40, GREEN).save("icons/dot-green.png")
circle_icon(40, RED).save("icons/dot-red.png")
circle_icon(40, YELLOW).save("icons/dot-yellow.png")

print("All icons generated in icons/")

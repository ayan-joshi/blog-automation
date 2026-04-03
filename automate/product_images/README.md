# Product Reference Images

Drop your product photos here. The image generator uses these as IP-Adapter
references when generating thumbnails for product posts — so the generated image
matches the real product's colour and shape.

## Required files

| Filename            | Product                          | Used for posts about…                     |
|---------------------|----------------------------------|-------------------------------------------|
| `ele-teether.jpg`   | Ele Ring Teether (sage green)    | Teething, drooling, silicone, BIS, amber  |
| `kiko-teether.jpg`  | Kiko Bear Teether (cream)        | Kiko, bear teether, no-drop teether       |
| `my-first-book.jpg` | My First Book Set (cloth books)  | Cloth books, high contrast, visual dev    |
| `newborn-kit.jpg`   | Newborn Essentials Kit           | Newborn kit, essentials, gifts            |

## Image tips

- Use a clean product-on-white or product-on-light-background photo
- JPEG or PNG, any size (fal.ai handles resizing)
- The IP-Adapter weight is set to 0.25 — low enough to keep the lifestyle scene
  realistic, just enough to guide the product's colour and shape

## What happens without these files

If a file is missing, the generator falls back to text-to-image using the
detailed thumbnail prompt (which describes the product by name, colour, shape).
Results are still good — just not pixel-accurate to the actual product.

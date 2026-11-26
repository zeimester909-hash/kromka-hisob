from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os


def _font_paths(bold):
    """Android va Windows uchun shrift yo'llarini qaytaradi."""
    base = os.path.dirname(os.path.abspath(__file__))
    paths = []
    # 1) Kivy bilan birga keladigan Roboto (Android'da ham mavjud)
    try:
        from kivy.resources import resource_find
        name = "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf"
        found = resource_find(f"data/fonts/{name}")
        if found:
            paths.append(found)
    except Exception:
        pass
    # 2) Loyiha ichidagi assets papkasi
    for name in (("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
                 ("Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf")):
        paths.append(os.path.join(base, "assets", name))
        paths.append(name)
    # 3) Tizim shriftlari
    paths += ["/system/fonts/Roboto-Regular.ttf",
              "/system/fonts/DroidSans.ttf",
              "arialbd.ttf" if bold else "arial.ttf"]
    return paths


def _get_font(size, bold=False):
    for path in _font_paths(bold):
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    try:                       # Pillow >= 10.1
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def create_receipt_image(records, total_metr, total_summa, narx, output_dir,
                         title="KROMKA HISOBOTI"):
    """
    Qisqa chek rasmi: sarlavha + jami metr + jami summa + sana.
    Ro'yxatlar sonidan qat'i nazar rasm o'lchami bir xil bo'ladi.
    Qaytaradi: (rasm_yo'li, txt_yo'li)
    """
    os.makedirs(output_dir, exist_ok=True)

    W, H = 700, 520
    pad = 40

    bg = (16, 24, 42)
    panel = (24, 36, 60)
    text = (230, 240, 255)
    sub = (140, 170, 210)
    accent = (58, 140, 235)
    green = (80, 220, 130)
    line = (44, 64, 96)

    f_title = _get_font(40, bold=True)
    f_head = _get_font(26, bold=True)
    f_big = _get_font(44, bold=True)
    f_small = _get_font(20)

    now = datetime.now()
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 110], fill=accent)
    d.text((pad, 24), title, font=f_title, fill=(255, 255, 255))
    d.text((pad, 76), now.strftime("%d.%m.%Y   %H:%M"),
           font=f_small, fill=(225, 235, 250))

    y = 140
    d.rounded_rectangle([pad, y, W - pad, y + 110], radius=14, fill=panel)
    d.text((pad + 24, y + 20), "JAMI METR", font=f_head, fill=accent)
    d.text((pad + 24, y + 52), f"{total_metr:.2f} m", font=f_big, fill=text)
    narx_text = f"1 m = {narx:,.0f} so'm"
    tw = d.textlength(narx_text, font=f_small)
    d.text((W - pad - 24 - tw, y + 74), narx_text, font=f_small, fill=sub)

    y += 135
    d.rounded_rectangle([pad, y, W - pad, y + 110], radius=14, fill=panel)
    d.text((pad + 24, y + 20), "JAMI SUMMA", font=f_head, fill=green)
    d.text((pad + 24, y + 52), f"{total_summa:,.0f} so'm", font=f_big, fill=green)

    y = H - 70
    d.line([(pad, y - 12), (W - pad, y - 12)], fill=line, width=2)
    d.text((pad, y), f"Yozuvlar: {len(records)}   |   Kromka Hisoblagich",
           font=f_small, fill=sub)

    stamp = now.strftime("%Y%m%d_%H%M%S")
    img_path = os.path.join(output_dir, f"chek_{stamp}.png")
    img.save(img_path)

    txt_path = os.path.join(output_dir, f"hisobot_{stamp}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("=" * 50 + "\n")
        f.write("         KROMKA HISOBOTI\n")
        f.write("=" * 50 + "\n")
        f.write(f"Sana: {now.strftime('%d.%m.%Y %H:%M')}\n")
        f.write(f"1 metr narxi: {narx:,.0f} so'm\n")
        f.write("-" * 50 + "\n")
        f.write(f"{'Buyurtma':<14}{'Metr':>8}{'Summa':>16}\n")
        f.write("-" * 50 + "\n")
        for r in records:
            summa = r["metr"] * narx
            order = str(r["order"])[:13]
            f.write(f"{order:<14}{r['metr']:>8.2f}{summa:>16,.0f}\n")
            f.write(f"  {r['sana']}\n")
        f.write("-" * 50 + "\n")
        f.write(f"{'JAMI METR:':<14}{total_metr:>8.2f}\n")
        f.write(f"{'JAMI SUMMA:':<14}{total_summa:>16,.0f} so'm\n")
        f.write("=" * 50 + "\n")

    return img_path, txt_path

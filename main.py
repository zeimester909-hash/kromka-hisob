from kivy.utils import platform
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.image import Image

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.dialog import MDDialog

from datetime import datetime
import json
import os

from chek import create_receipt_image

# Klaviatura ochilganda kiritish maydoni ko'rinib turishi uchun
Window.softinput_mode = "below_target"

BG = (0.06, 0.09, 0.16, 1)
CARD = (0.10, 0.15, 0.25, 1)
BLUE = (0.35, 0.65, 1, 1)
GREEN = (0.4, 0.85, 0.55, 1)
SUB = (0.55, 0.68, 0.85, 1)


def fmt_num(value):
    """15000.0 -> '15000', 12.5 -> '12.5' (ilmiy yozuvsiz)."""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def parse_float(text):
    return float(text.strip().replace(",", ".").replace(" ", ""))


# ---------- Android: galereya / yuklamalarga saqlash va ulashish ----------
def android_save_and_share(path, mime, title):
    """
    Faylni MediaStore orqali ochiq papkaga saqlaydi (Android 10+ da
    ruxsat shart emas) va 'Ulashish' oynasini ochadi.
    Qaytaradi: saqlangan joy nomi.
    """
    from jnius import autoclass, cast

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Intent = autoclass("android.content.Intent")
    ContentValues = autoclass("android.content.ContentValues")
    activity = PythonActivity.mActivity
    resolver = activity.getContentResolver()

    values = ContentValues()
    values.put("_display_name", os.path.basename(path))
    values.put("mime_type", mime)
    if mime.startswith("image/"):
        collection = autoclass(
            "android.provider.MediaStore$Images$Media").EXTERNAL_CONTENT_URI
        values.put("relative_path", "Pictures/Kromka")
        where = "Pictures/Kromka"
    else:
        collection = autoclass(
            "android.provider.MediaStore$Downloads").EXTERNAL_CONTENT_URI
        values.put("relative_path", "Download/Kromka")
        where = "Download/Kromka"

    uri = resolver.insert(collection, values)
    stream = resolver.openOutputStream(uri)
    with open(path, "rb") as f:
        stream.write(bytearray(f.read()))
    stream.flush()
    stream.close()

    intent = Intent(Intent.ACTION_SEND)
    intent.setType(mime)
    intent.putExtra(Intent.EXTRA_STREAM, cast("android.os.Parcelable", uri))
    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    activity.startActivity(Intent.createChooser(intent, title))
    return where


def stretch(btn, parent=None, minus=0):
    """KivyMD tugmasini butun kenglikka cho'zadi (kv qoidasi size_hint ni
    o'chirib qo'yadi, shuning uchun keyingi kadrda qayta yoqamiz)."""
    Clock.schedule_once(lambda dt: setattr(btn, "size_hint_x", 1), 0)
    return btn


class KromkaApp(MDApp):

    dialog = None
    receipt_path = None
    txt_path = None
    narx = 0.0          # 1 metr narxi (so'm)

    # ---------- Hayot sikli ----------
    def build(self):
        self.title = "Kromka Hisoblagich"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Dark"
        Window.clearcolor = BG
        self.filter_date_from = ""
        self.filter_date_to = ""

        self.data_dir = self.user_data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.data_file = os.path.join(self.data_dir, "kromka_data.json")
        self.chek_dir = os.path.join(self.data_dir, "cheklar")
        os.makedirs(self.chek_dir, exist_ok=True)

        bundled = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "kromka_data.json")
        if not os.path.exists(self.data_file) and os.path.exists(bundled):
            try:
                with open(bundled, "r", encoding="utf-8") as s, \
                        open(self.data_file, "w", encoding="utf-8") as t:
                    t.write(s.read())
            except Exception:
                pass

        data = self.load_data()
        self.records = data.get("records", [])
        self.narx = data.get("narx", 0.0)

        # Status bar ostida qolmaslik uchun yuqoridan bo'sh joy
        top_pad = dp(28) if platform == "android" else dp(8)
        root = MDBoxLayout(orientation="vertical", spacing=dp(10),
                           padding=(dp(12), top_pad, dp(12), dp(10)))
        root.md_bg_color = BG

        # --- Sarlavha ---
        root.add_widget(MDLabel(
            text="[b]KROMKA HISOBLAGICH[/b]", markup=True, halign="center",
            font_style="H6", theme_text_color="Custom", text_color=BLUE,
            size_hint_y=None, height=dp(34),
        ))

        # --- Jami kartasi ---
        totals = MDCard(
            orientation="horizontal", padding=dp(12), spacing=dp(8),
            size_hint_y=None, height=dp(78), md_bg_color=CARD,
            radius=[dp(14)], elevation=0,
        )
        self.metr_label = self._stat_block(totals, "JAMI METR", BLUE)
        self.summa_label = self._stat_block(totals, "JAMI SUMMA", GREEN)
        self.count_label = self._stat_block(totals, "YOZUV", SUB, hint_x=0.5)
        root.add_widget(totals)

        # --- Kiritish kartasi ---
        inputs = MDCard(
            orientation="vertical", padding=dp(12), spacing=dp(6),
            size_hint_y=None, md_bg_color=CARD, radius=[dp(14)],
            elevation=0,
        )
        inputs.bind(minimum_height=inputs.setter("height"))

        narx_row = MDBoxLayout(adaptive_height=True, spacing=dp(6))
        self.narx_input = MDTextField(
            hint_text="1 metr narxi (so'm)", mode="rectangle",
            input_type="number", size_hint_x=1,
        )
        if self.narx > 0:
            self.narx_input.text = fmt_num(self.narx)
        narx_row.add_widget(self.narx_input)
        narx_row.add_widget(MDIconButton(
            icon="content-save", theme_icon_color="Custom",
            icon_color=(0.7, 0.5, 1, 1), pos_hint={"center_y": 0.55},
            on_release=self.save_narx,
        ))
        inputs.add_widget(narx_row)

        row = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        self.order_input = MDTextField(
            hint_text="Buyurtma", mode="rectangle", size_hint_x=0.5,
        )
        self.metr_input = MDTextField(
            hint_text="Metr", mode="rectangle", input_type="number",
            size_hint_x=0.5,
        )
        row.add_widget(self.order_input)
        row.add_widget(self.metr_input)
        inputs.add_widget(row)

        add_btn = MDRaisedButton(
            text="+  QO'SHISH", md_bg_color=(0.15, 0.55, 0.85, 1),
            on_release=self.add_record,
        )
        stretch(add_btn, inputs, minus=dp(24))
        inputs.add_widget(add_btn)
        root.add_widget(inputs)

        # --- Sana filtri ---
        filters = MDCard(
            orientation="vertical", padding=dp(10), spacing=dp(4),
            size_hint_y=None, md_bg_color=CARD, radius=[dp(14)],
            elevation=0,
        )
        filters.bind(minimum_height=filters.setter("height"))

        date_row = MDBoxLayout(adaptive_height=True, spacing=dp(6))
        self.date_from_input = MDTextField(
            hint_text="Dan (kun.oy.yil)", mode="rectangle", size_hint_x=0.5,
        )
        self.date_to_input = MDTextField(
            hint_text="Gacha (kun.oy.yil)", mode="rectangle", size_hint_x=0.5,
        )
        self.date_from_input.bind(text=self._on_filter_text)
        self.date_to_input.bind(text=self._on_filter_text)
        date_row.add_widget(self.date_from_input)
        date_row.add_widget(self.date_to_input)
        date_row.add_widget(MDIconButton(
            icon="close-circle", theme_icon_color="Custom",
            icon_color=SUB, pos_hint={"center_y": 0.55},
            on_release=self.clear_filters,
        ))
        filters.add_widget(date_row)
        root.add_widget(filters)

        # --- Ro'yxat ---
        scroll = MDScrollView()
        self.records_list = MDBoxLayout(
            orientation="vertical", spacing=dp(6),
            size_hint_y=None, padding=(0, dp(2)),
        )
        self.records_list.bind(minimum_height=self.records_list.setter("height"))
        scroll.add_widget(self.records_list)
        root.add_widget(scroll)

        # --- Pastki tugmalar ---
        bottom = MDBoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        chek_btn = MDRaisedButton(
            text="CHEK YARATISH", pos_hint={"center_y": 0.5},
            md_bg_color=(0.1, 0.45, 0.8, 1), on_release=self.create_receipt,
        )
        stretch(chek_btn, bottom, minus=dp(64))
        bottom.add_widget(chek_btn)
        bottom.add_widget(MDIconButton(
            icon="delete-sweep", theme_icon_color="Custom",
            icon_color=(1, 0.4, 0.4, 1), pos_hint={"center_y": 0.5},
            on_release=self.confirm_clear,
        ))
        root.add_widget(bottom)

        self.refresh_list()
        return root

    def _stat_block(self, parent, caption, color, hint_x=1):
        box = MDBoxLayout(orientation="vertical", size_hint_x=hint_x)
        box.add_widget(MDLabel(
            text=caption, font_style="Caption", theme_text_color="Custom",
            text_color=SUB, size_hint_y=None, height=dp(18),
        ))
        value = MDLabel(
            text="0", font_style="Subtitle1", bold=True,
            theme_text_color="Custom", text_color=color, shorten=True,
        )
        box.add_widget(value)
        parent.add_widget(box)
        return value

    # ---------- Ma'lumotlar ----------
    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, list):          # eski format
                    records, narx = data, 0.0
                elif isinstance(data, dict):
                    records = data.get("records", [])
                    narx = float(data.get("narx", 0.0) or 0.0)
                else:
                    return {"records": [], "narx": 0.0}

                normalized = []
                for index, record in enumerate(records):
                    if not isinstance(record, dict):
                        continue
                    try:
                        metr = float(record.get("metr", 0))
                    except (TypeError, ValueError):
                        continue
                    if metr <= 0:
                        continue
                    normalized.append({
                        "order": str(record.get("order") or f"Eski {index + 1}"),
                        "metr": metr,
                        "sana": str(record.get("sana") or
                                    datetime.now().strftime("%d.%m.%Y %H:%M")),
                    })
                return {"records": normalized, "narx": narx}
            except Exception:
                pass
        return {"records": [], "narx": 0.0}

    def save_data(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump({"records": self.records, "narx": self.narx},
                      f, ensure_ascii=False, indent=2)

    def _total_metr(self):
        return sum(r["metr"] for r in self.records)

    def _total_summa(self):
        return self._total_metr() * self.narx

    def _update_totals(self):
        self.metr_label.text = f"{self._total_metr():.2f} m"
        self.summa_label.text = f"{self._total_summa():,.0f}"
        self.count_label.text = str(len(self.records))

    # ---------- Narx ----------
    def save_narx(self, instance):
        try:
            narx = parse_float(self.narx_input.text)
            if narx < 0:
                raise ValueError
        except ValueError:
            self.toast("Narxni to'g'ri kiriting")
            return
        self.narx = narx
        self.save_data()
        self.refresh_list()
        self.toast(f"Narx saqlandi: {narx:,.0f} so'm")

    # ---------- Qo'shish ----------
    def add_record(self, instance):
        order = self.order_input.text.strip()
        if not order:
            self.toast("Buyurtma raqamini kiriting")
            return
        try:
            metr = parse_float(self.metr_input.text)
            if metr <= 0:
                raise ValueError
        except ValueError:
            self.toast("Metrni to'g'ri kiriting")
            return

        self.records.insert(0, {
            "order": order, "metr": metr,
            "sana": datetime.now().strftime("%d.%m.%Y %H:%M"),
        })
        self.save_data()
        self.order_input.text = ""
        self.metr_input.text = ""
        self.refresh_list()

    # ---------- O'chirish ----------
    def confirm_delete(self, index):
        if not (0 <= index < len(self.records)):
            return
        rec = self.records[index]
        self.show_dialog(
            title="O'chirishni tasdiqlang",
            text=f"{rec['order']} - {rec['metr']:.2f} m\n\nBu yozuv o'chiriladi.",
            buttons=[
                MDFlatButton(text="BEKOR", on_release=self._close),
                MDRaisedButton(
                    text="O'CHIRISH", md_bg_color=(0.85, 0.25, 0.25, 1),
                    on_release=lambda *_: self._do_delete(index)),
            ],
        )

    def _do_delete(self, index):
        if 0 <= index < len(self.records):
            del self.records[index]
            self.save_data()
            self.refresh_list()
        self._close()

    def confirm_clear(self, instance):
        if not self.records:
            self.toast("Ro'yxat bo'sh")
            return
        self.show_dialog(
            title="Tasdiqlash",
            text="Barcha yozuvlarni o'chirmoqchimisiz?",
            buttons=[
                MDFlatButton(text="BEKOR", on_release=self._close),
                MDRaisedButton(
                    text="O'CHIRISH", md_bg_color=(0.85, 0.25, 0.25, 1),
                    on_release=self._do_clear),
            ],
        )

    def _do_clear(self, instance):
        self.records = []
        self.save_data()
        self.refresh_list()
        self._close()

    # ---------- Tahrirlash ----------
    def edit_record(self, index):
        if not (0 <= index < len(self.records)):
            return
        rec = self.records[index]

        self._edit_order = MDTextField(
            text=rec["order"], hint_text="Buyurtma raqami", mode="rectangle")
        self._edit_metr = MDTextField(
            text=fmt_num(rec["metr"]), hint_text="Metr",
            input_type="number", mode="rectangle")

        content = MDBoxLayout(orientation="vertical", spacing=dp(8),
                              size_hint_y=None, height=dp(150))
        content.add_widget(self._edit_order)
        content.add_widget(self._edit_metr)

        self._edit_index = index
        self.show_dialog(
            title="Tahrirlash", text=None,
            content_widget=content, content_height=150,
            buttons=[
                MDFlatButton(text="BEKOR", on_release=self._close),
                MDRaisedButton(
                    text="SAQLASH", md_bg_color=(0.15, 0.55, 0.85, 1),
                    on_release=self._do_edit),
            ],
        )

    def _do_edit(self, instance):
        idx = self._edit_index
        if not (0 <= idx < len(self.records)):
            self._close()
            return
        order = self._edit_order.text.strip()
        if not order:
            self.toast("Buyurtma raqamini kiriting")
            return
        try:
            metr = parse_float(self._edit_metr.text)
            if metr <= 0:
                raise ValueError
        except ValueError:
            self.toast("Metrni to'g'ri kiriting")
            return

        self.records[idx]["order"] = order
        self.records[idx]["metr"] = metr
        self.save_data()
        self.refresh_list()
        self._close()

    # ---------- Ro'yxat ----------
    def refresh_list(self):
        self.records_list.clear_widgets()
        self._update_totals()

        if not self.records:
            self.records_list.add_widget(MDLabel(
                text="Hozircha yozuvlar yo'q", halign="center",
                theme_text_color="Secondary",
                size_hint_y=None, height=dp(60),
            ))
            return

        filtered = self._filtered_records()
        if not filtered:
            self.records_list.add_widget(MDLabel(
                text="Mos yozuvlar topilmadi", halign="center",
                theme_text_color="Secondary",
                size_hint_y=None, height=dp(60),
            ))
            return

        for index, rec in enumerate(self.records):
            if rec not in filtered:
                continue
            self.records_list.add_widget(self._build_row(index, rec))

    def _parse_date(self, text):
        try:
            return datetime.strptime(text.strip(), "%d.%m.%Y").date()
        except (TypeError, ValueError):
            return None

    def _filtered_records(self):
        date_from = self._parse_date(self.filter_date_from)
        date_to = self._parse_date(self.filter_date_to)

        result = []
        for rec in self.records:
            record_date = self._parse_date(str(rec.get("sana", "")).strip()[:10])
            if date_from and (record_date is None or record_date < date_from):
                continue
            if date_to and (record_date is None or record_date > date_to):
                continue
            result.append(rec)
        return result

    def _on_filter_text(self, instance, value):
        if instance is self.date_from_input:
            self.filter_date_from = value
        elif instance is self.date_to_input:
            self.filter_date_to = value
        self.refresh_list()

    def clear_filters(self, instance):
        self.date_from_input.text = ""
        self.date_to_input.text = ""
        self.filter_date_from = ""
        self.filter_date_to = ""
        self.refresh_list()

    def _build_row(self, index, rec):
        summa = rec["metr"] * self.narx

        card = MDCard(
            orientation="horizontal", padding=(dp(12), dp(4), dp(2), dp(4)),
            spacing=dp(2), size_hint_y=None, height=dp(72),
            md_bg_color=CARD, radius=[dp(12)], elevation=0,
        )

        text_box = MDBoxLayout(orientation="vertical", size_hint_x=1)
        text_box.add_widget(MDLabel(
            text=f"[b]{rec['order']}[/b]   {rec['metr']:.2f} m",
            markup=True, font_style="Subtitle1",
            theme_text_color="Custom", text_color=(0.9, 0.95, 1, 1),
            shorten=True, shorten_from="right",
        ))
        text_box.add_widget(MDLabel(
            text=f"{summa:,.0f} so'm", font_style="Body2",
            theme_text_color="Custom", text_color=GREEN,
        ))
        text_box.add_widget(MDLabel(
            text=rec["sana"], font_style="Caption",
            theme_text_color="Custom", text_color=SUB,
        ))
        card.add_widget(text_box)

        card.add_widget(MDIconButton(
            icon="pencil", theme_icon_color="Custom",
            icon_color=(0.35, 0.7, 1, 1), pos_hint={"center_y": 0.5},
            on_release=lambda x, idx=index: self.edit_record(idx),
        ))
        card.add_widget(MDIconButton(
            icon="delete", theme_icon_color="Custom",
            icon_color=(1, 0.45, 0.45, 1), pos_hint={"center_y": 0.5},
            on_release=lambda x, idx=index: self.confirm_delete(idx),
        ))
        return card

    # ---------- Chek ----------
    def create_receipt(self, instance):
        if not self.records:
            self.toast("Chek yaratish uchun yozuvlar yo'q")
            return
        if self.narx <= 0:
            self.toast("Avval 1 metr narxini kiriting")
            return

        try:
            self.receipt_path, self.txt_path = create_receipt_image(
                self.records, self._total_metr(), self._total_summa(),
                self.narx, self.chek_dir)
        except Exception as e:
            self.toast(f"Chek yaratib bo'lmadi: {e}")
            return

        img = Image(source=self.receipt_path, fit_mode="contain",
                    size_hint_y=None, height=dp(240))
        self.show_dialog(
            title="Chek tayyor", text=None,
            content_widget=img, content_height=250,
            buttons=[
                MDFlatButton(text="YOPISH", on_release=self._close),
                MDRaisedButton(text="TXT", on_release=self.share_txt),
                MDRaisedButton(text="RASM", on_release=self.share_image),
            ],
        )

    def share_image(self, instance):
        self._share(self.receipt_path, "image/png", "Kromka cheki")

    def share_txt(self, instance):
        self._share(self.txt_path, "text/plain", "Kromka hisoboti")

    def _share(self, path, mime, title):
        if not path:
            return
        if platform == "android":
            try:
                where = android_save_and_share(path, mime, title)
                self.toast(f"Saqlandi: {where}")
            except Exception as e:
                self.toast(f"Ulashib bo'lmadi: {e}")
        else:
            self.toast(f"Fayl: {path}")

    # ---------- Dialog / Toast ----------
    def _close(self, *args):
        if self.dialog:
            self.dialog.dismiss()

    def show_dialog(self, title, text, buttons=None, content_widget=None,
                    content_height=0):
        if text and not content_widget:
            self.dialog = MDDialog(
                title=title, text=text,
                buttons=buttons or [MDFlatButton(text="YOPISH",
                                                 on_release=self._close)],
            )
        else:
            content = MDBoxLayout(orientation="vertical", spacing=dp(8),
                                  size_hint_y=None,
                                  height=dp(content_height))
            content.add_widget(content_widget)
            self.dialog = MDDialog(
                title=title, type="custom", content_cls=content,
                buttons=buttons or [MDFlatButton(text="YOPISH",
                                                 on_release=self._close)],
            )
        self.dialog.open()

    def toast(self, message):
        try:
            from kivymd.toast import toast
            toast(message)
        except Exception:
            self.show_dialog("Xabar", message)


if __name__ == "__main__":
    KromkaApp().run()

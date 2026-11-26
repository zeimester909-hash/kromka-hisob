APK OLISH (eng oson yo'l - GitHub Actions, kompyuterda hech narsa o'rnatish shart emas)

1. github.com da bepul akkaunt oching va yangi (Private bo'lsa ham bo'ladi) repository yarating.
2. Shu papkadagi BARCHA fayllarni (".github" papkasi bilan birga!) repository'ga yuklang.
   (GitHub Desktop yoki "Add file > Upload files" orqali; yashirin .github papkasini ham tanlang.)
3. Repository'da "Actions" bo'limiga kiring -> "Build APK" -> "Run workflow".
4. 15-30 daqiqadan keyin tugagach, ish sahifasi pastidagi "Artifacts" ichidan
   "kromka-apk" ni yuklab oling -> zip ichida .apk fayl bor.
5. APK ni telefonga o'tkazib, "Noma'lum manbalardan o'rnatish"ga ruxsat berib o'rnating.

Kompyuterda sinash (Windows):
   pip install kivy==2.3.0 kivymd==1.1.1 pillow
   python main.py

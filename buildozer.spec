[app]

title = Kromka Hisoblagich
package.name = kromkahisob
package.domain = org.kromka

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json
source.exclude_dirs = bin,.buildozer,.github,__pycache__

version = 1.0

# Kivy 2.3.0 + KivyMD 1.1.1 (kivymd 1.1.1 ga mos). Python versiyasini
# python-for-android o'zi tanlaydi (hostpython3 ni qo'lda yozmang).
requirements = python3,kivy==2.3.0,kivymd==1.1.1,pillow,pyjnius,android

# Kivy 2.3.0 bilan mos keladigan barqaror python-for-android tarmog'i.
p4a.branch = release-2024.01.21

# Ikonka va yuklanish ekrani
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #10182A

orientation = portrait
fullscreen = 0

# Ruxsatlar kerak emas: fayllar MediaStore orqali saqlanadi (Android 10+)
android.permissions =

android.api = 34
android.minapi = 29
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True

log_level = 2

[buildozer]
log_level = 2
warn_on_root = 0

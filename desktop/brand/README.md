# شعار openNews / openNews identity

مصدر الشعار الحالي هو رمز الصحيفة في `app-icon.svg` و`mark.svg`. تستخدم الواجهة المسار نفسه في `desktop/src/brand.tsx`. ملفات المنصّة اللازمة للبناء موجودة فقط في `desktop/src-tauri/icons/`.

The current identity is the newspaper symbol. `app-icon.svg` supplies the application tile; `mark.svg` supplies the transparent monochrome mark. React uses the same geometry in `desktop/src/brand.tsx`. Required platform assets live in `desktop/src-tauri/icons/`.

From the repository root, generate assets into a temporary directory:

```sh
npm --prefix desktop run tauri -- icon brand/app-icon.svg -o /tmp/opennews-app-icons
npm --prefix desktop run tauri -- icon brand/mark.svg -p 32 -o /tmp/opennews-tray-icon
```

Copy the app's `icon.png` and `icon.icns` into `desktop/src-tauri/icons/`, and the mark's `32x32.png` as `tray.png`. The tray is a template image tinted by macOS. Generated Windows, Android and iOS files are not tracked because those platforms are not currently distributed.

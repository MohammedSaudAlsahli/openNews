"""Static loopback landing page. Never interpolate OAuth parameters or account data."""
def callback_page(success, language='en'):
    arabic = language == 'ar'
    title = ('تم تسجيل الدخول بنجاح' if success else 'لم يكتمل تسجيل الدخول') if arabic else ('Authorization successful' if success else 'Sign-in was not completed')
    detail = ('تم ربط OpenStudio بحساب ChatGPT.' if success else 'ارجع إلى OpenStudio وحاول تسجيل الدخول مجددًا.') if arabic else ('OpenStudio is now connected to ChatGPT.' if success else 'Return to OpenStudio and try signing in again.')
    footer = 'يمكنك إغلاق هذه النافذة والعودة إلى التطبيق.' if arabic else 'You can close this window and return to the app.'
    return f'''<!doctype html><html lang="{'ar' if arabic else 'en'}" dir="{'rtl' if arabic else 'ltr'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>
:root {{ color-scheme:light dark; font-family:system-ui,-apple-system,sans-serif; }}
body {{ margin:0; min-height:100vh; display:grid; place-items:center; background:light-dark(#f5f5f7,#101011); color:light-dark(#202024,#f4f4f5); }}
main {{ margin:24px; padding:44px 32px; max-width:440px; text-align:center; border:1px solid light-dark(#dedee3,#303034); border-radius:20px; background:light-dark(white,#19191c); }}
.brand {{ font-size:15px; font-weight:600; color:light-dark(#646469,#a1a1aa); }}
.status {{ color:{'#30a46c' if success else '#e07036'}; font-size:42px; margin:30px 0 16px; }}
h1 {{ font-size:23px; font-weight:600; }} p {{ line-height:1.7; }} .hint {{ color:light-dark(#646469,#a1a1aa); font-size:14px; margin-top:28px; }}
</style></head><body><main><div class="brand">OpenStudio</div><div class="status" aria-hidden="true">{'✓' if success else '!'}</div><h1>{title}</h1><p>{detail}</p><p class="hint">{footer}</p></main></body></html>'''.encode()

"""
Django settings for Ombor Nazorat project.
Local warehouse management system.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-ombor-nazorat-change-this-in-production-!@#$%^&*()'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']  # vaqtincha (demo uchun)


# Application definition
INSTALLED_APPS = [
    'jazzmin',  # Must be before django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Local apps
    'accounts',
    'inventory',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database - PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ombor_nazorat',
        'USER': 'postgres',
        'PASSWORD': '96970204',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login settings
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Session settings
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True

# ============================================
# Custom Settings for Ombor Nazorat
# ============================================

# Face verification timeout (seconds) - 5 minutes
FACE_VERIFICATION_TIMEOUT = 300

# Backup settings - Windows PostgreSQL path
PG_DUMP_PATH = r"D:\Postgres\bin\pg_dump.exe"

# Pagination
DEFAULT_PAGE_SIZE = 50

CSRF_TRUSTED_ORIGINS = [
    "https://*.ngrok-free.app",
    "https://*.ngrok.io",
]

# ============================================
# Jazzmin Admin Theme Settings (Refined)
# ============================================
JAZZMIN_SETTINGS = {
    # Title / Branding
    "site_title": "Ombor Nazorat",
    "site_header": "Ombor Nazorat",
    "site_brand": "📦 Ombor Nazorat",
    "site_logo": None,
    "login_logo": None,
    "site_logo_classes": "img-circle",
    "site_icon": None,

    # Welcome text
    "welcome_sign": "📦 Ombor boshqaruv paneli",
    "copyright": "Ombor Nazorat © 2026",

    # Search model (custom user bo‘lsa accounts.User bo‘lsin)
    "search_model": ["accounts.User", "inventory.Product", "inventory.Movement"],

    # User avatar
    "user_avatar": None,

    # Top menu links (ko‘proq amaliy)
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index"},
        {"name": "Ombor (sayt)", "url": "/", "new_window": True},
        {"name": "Mahsulotlar", "url": "/products/", "new_window": True},
        {"name": "Harakatlar", "url": "/movements/", "new_window": True},
    ],

    # Side menu
    "show_sidebar": True,
    "navigation_expanded": False,   # avvaliga yig‘iq — toza ko‘rinadi
    "hide_apps": [],
    "hide_models": [],

    # Order apps
    "order_with_respect_to": ["accounts", "inventory", "auth"],

    # Icons (model nomlarini sizdagi real nomlarga mosladim)
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.group": "fas fa-users",

        "accounts.User": "fas fa-user-shield",

        "inventory.Category": "fas fa-tags",
        "inventory.Product": "fas fa-box-open",
        "inventory.Stock": "fas fa-warehouse",
        "inventory.Movement": "fas fa-right-left",
        "inventory.MovementItem": "fas fa-list-check",
        "inventory.Employee": "fas fa-id-badge",
    },

    "default_icon_parents": "fas fa-angle-right",
    "default_icon_children": "far fa-circle",

    # Related modal
    "related_modal_active": True,

    # UI Tweaks
    "custom_css": "css/admin_custom.css",   # xohlasangiz keyin qo‘shamiz
    "custom_js": None,
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,

    # Change view
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "auth.group": "vertical_tabs",
        "accounts.user": "collapsible",
    },
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": True,
    "body_small_text": False,
    "brand_small_text": False,

    # Navbar / Sidebar (zamonaviyroq)
    "navbar": "navbar-dark",
    "brand_colour": "navbar-dark",

    # Accent rangni bir xil ushlab turamiz
    "accent": "accent-info",                # primary o‘rniga info — ko‘zni kam charchatadi

    "navbar_fixed": True,
    "footer_fixed": False,

    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-info",         # primary o‘rniga info

    "sidebar_disable_expand": False,
    "sidebar_nav_small_text": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,      # zichroq, ombor uchun qulay
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": True,         # tekis, zamonaviy

    # Theme
    "theme": "darkly",
    "dark_mode_theme": "darkly",

    # Buttons
    "button_classes": {
        "primary": "btn-info",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
}

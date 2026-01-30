import os
from pathlib import Path

# プロジェクトのルートディレクトリ（config/settings.py から見た2つ上の階層）
BASE_DIR = Path(__file__).resolve().parent.parent

# ⚠️ 本番公開時はより複雑な文字列に変更することを推奨します
SECRET_KEY = 'django-insecure-new-pos-system-key'

# ⚠️ サーバー公開時は False に変更してください
DEBUG = True

# 💡 公開ドメインが決まったらここに追加します（例: ['your-domain.com']）
ALLOWED_HOSTS = ['*']

# --- アプリケーション定義 ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'catalog', 
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
        'DIRS': [BASE_DIR / 'templates'], # 共通ベーステンプレートの読み込み用
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

# --- データベース設定（SQLite3を継続使用） ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --- 言語・時刻設定 ---
LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_TZ = True

# --- ✨ 静的ファイル (CSS/JS) の設定 ---
STATIC_URL = '/static/'

# 💡 本番環境で collectstatic を実行した際にファイルが集約される場所
STATIC_ROOT = BASE_DIR / 'staticfiles'

# 💡 開発中に使用する静的ファイルのディレクトリ設定
STATICFILES_DIRS = [BASE_DIR / 'static']

# --- ✨ メディアファイル (女の子たちの画像) の設定 ---
MEDIA_URL = '/media/'

# 💡 実際に画像ファイルが保存・参照されるディレクトリ
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- 認証設定 ---
LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/admin/'

# --- 🚀 パフォーマンス・制限緩和設定 ---
# 💡 大量画像の一括アップロードに対応するための設定
DATA_UPLOAD_MAX_NUMBER_FILES = 1000 
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600
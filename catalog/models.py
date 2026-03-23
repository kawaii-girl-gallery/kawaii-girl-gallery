from django.db import models
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
import os
import io

# --- 画像加工関数（リサイズ ＋ ウォーターマーク） ---
def process_product_image(img_path):
    try:
        # 1. 画像を開いてRGBAに変換
        img = Image.open(img_path).convert("RGBA")
        
        # 2. リサイズ処理
        max_size = 1200
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)

        # 3. ウォーターマーク用レイヤー作成
        txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        
        sample_size = int(img.width / 4.5) 
        stamp_size = int(img.width / 18)

        # Linuxで使えるフォントを順番に試す
        def load_font(size):
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
                "ariblk.ttf",
                "meiryo.ttc",
                "msgothic.ttc",
            ]
            for path in font_paths:
                try:
                    return ImageFont.truetype(path, size)
                except:
                    continue
            # どれも使えない場合はデフォルトを大きく
            return ImageFont.load_default(size=max(size, 20))

        font_sample = load_font(sample_size)
        font_stamp = load_font(stamp_size)

        # SAMPLE（中央）
        text_s = "SAMPLE"
        s_l, s_t, s_r, s_b = draw.textbbox((0, 0), text_s, font=font_sample)
        sx = (img.width - (s_r - s_l)) / 2 - s_l
        sy = (img.height - (s_b - s_t)) / 2 - s_t
        draw.text((sx, sy), text_s, fill=(255, 255, 255, 160), font=font_sample)

        # スタンプ（右下）
        text_k = "kawaii女の子図鑑"
        k_l, k_t, k_r, k_b = draw.textbbox((0, 0), text_k, font=font_stamp)
        w_k, h_k = k_r - k_l, k_b - k_t
        padding, inner = int(img.width * 0.05), int(stamp_size * 0.4)
        r_x1, r_y1 = img.width - padding, img.height - padding
        r_x0, r_y0 = r_x1 - (w_k + inner * 2), r_y1 - (h_k + inner * 2)
        
        draw.rectangle([r_x0, r_y0, r_x1, r_y1], outline=(200, 0, 0, 200), width=6)
        draw.text((r_x0 + inner - k_l, r_y0 + inner - k_t), text_k, fill=(200, 0, 0, 200), font=font_stamp)

        # 合成してJPEGで保存
        out = Image.alpha_composite(img, txt_layer)
        out.convert("RGB").save(img_path, "JPEG", quality=90, optimize=True)
        print(f"Image processed successfully: {img_path}")
        
    except Exception as e:
        print(f"Image Processing Error: {e}")

# --- 商品モデル ---
class Product(models.Model):
    CAT_CHOICES = [('A4', 'A4サイズポスター'), ('TCG', 'トレーディングカード')]
    category = models.CharField('種別', max_length=10, choices=CAT_CHOICES)
    name = models.CharField('商品名', max_length=255)
    price = models.IntegerField('金額', default=88)
    image = models.ImageField('画像', upload_to='products/')
    is_archived = models.BooleanField('保管庫送り', default=False)
    created_at = models.DateTimeField('登録日時', auto_now_add=True)

    class Meta:
        verbose_name = '全商品一覧'
        verbose_name_plural = '全商品一覧'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            process_product_image(self.image.path)

# --- 売上記録モデル ---
class Sale(models.Model):
    product_name = models.CharField('商品名', max_length=255)
    price = models.IntegerField('売上金額')
    category = models.CharField('種別', max_length=50, blank=True)
    sold_at = models.DateTimeField('販売日時', auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='購入者'
    )

    class Meta:
        verbose_name = '売上データ'
        verbose_name_plural = '売上データ一覧'

    def __str__(self):
        u = self.user.username if self.user else "ゲスト"
        return f"{self.sold_at.strftime('%Y-%m-%d %H:%M')} - {self.product_name} ({u})"

# --- プロキシモデル ---
class Show_ProductList_A4(Product):
    class Meta:
        proxy = True
        verbose_name = '商品一覧'
        verbose_name_plural = '商品一覧'

class Z_Archive_A4(Product):
    class Meta:
        proxy = True
        verbose_name = '保管庫'
        verbose_name_plural = '保管庫'

class Show_ProductList_TCG(Product):
    class Meta:
        proxy = True
        verbose_name = '商品一覧'
        verbose_name_plural = '商品一覧'

class Z_Archive_TCG(Product):
    class Meta:
        proxy = True
        verbose_name = '保管庫'
        verbose_name_plural = '保管庫'

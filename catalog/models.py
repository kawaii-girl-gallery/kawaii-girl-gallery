from django.db import models
from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from PIL import Image, ImageDraw, ImageFont
import os
import io
from io import BytesIO


# --- 商品モデル ---
class Product(models.Model):
    CAT_CHOICES = [('A4', 'A4サイズポスター'), ('TCG', 'トレーディングカード')]
    category = models.CharField('種別', max_length=10, choices=CAT_CHOICES)
    name = models.CharField('商品名', max_length=255)
    price = models.IntegerField('金額', default=88)
    
    # ImageKit 用フィールド
    image_url = models.URLField('画像URL', max_length=500, blank=True, default='')
    imagekit_file_id = models.CharField('ImageKit File ID', max_length=100, blank=True, default='')
    
    # 一時的に画像を受け取るためのフィールド（アップロードフォーム用）
    image = models.ImageField('画像', upload_to='products/', blank=True, null=True)
    
    is_archived = models.BooleanField('保管庫送り', default=False)
    duration_days = models.IntegerField('掲載日数', default=6)
    created_at = models.DateTimeField('登録日時', auto_now_add=True)

    class Meta:
        verbose_name = '全商品一覧'
        verbose_name_plural = '全商品一覧'

    def __str__(self):
        return self.name

    def _process_image_in_memory(self, img_file, add_watermark=True):
        """画像をメモリで処理（リサイズ + SAMPLE透かし + スタンプ）"""
        img_data = img_file.read()
        if hasattr(img_file, 'seek'):
            img_file.seek(0)
        
        img = Image.open(BytesIO(img_data)).convert("RGBA")
        max_size = 1200
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
        
        txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        sample_size = int(img.width / 4.5)
        stamp_size = int(img.width / 18)

        def load_font_en(size):
            for path in [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            ]:
                try:
                    return ImageFont.truetype(path, size)
                except:
                    continue
            return ImageFont.load_default(size=max(size, 20))

        def load_font_ja(size):
            import django.conf
            base_dir = django.conf.settings.BASE_DIR
            for path in [
                os.path.join(base_dir, "catalog", "static", "catalog", "fonts", "NotoSansJP-VariableFont_wght.ttf"),
                os.path.join(base_dir, "staticfiles", "catalog", "fonts", "NotoSansJP-VariableFont_wght.ttf"),
            ]:
                try:
                    return ImageFont.truetype(path, size)
                except:
                    continue
            return ImageFont.load_default(size=max(size, 20))

        font_sample = load_font_en(sample_size)
        font_stamp = load_font_ja(stamp_size)

        # SAMPLE透かし
        if add_watermark:
            text_s = "SAMPLE"
            s_l, s_t, s_r, s_b = draw.textbbox((0, 0), text_s, font=font_sample)
            sx = (img.width - (s_r - s_l)) / 2 - s_l
            sy = (img.height - (s_b - s_t)) / 2 - s_t
            draw.text((sx, sy), text_s, fill=(255, 255, 255, 160), font=font_sample)

        # スタンプ
        text_k = "kawaii女の子図鑑"
        k_l, k_t, k_r, k_b = draw.textbbox((0, 0), text_k, font=font_stamp)
        w_k, h_k = k_r - k_l, k_b - k_t
        padding, inner = int(img.width * 0.05), int(stamp_size * 0.4)
        r_x1, r_y1 = img.width - padding, img.height - padding
        r_x0, r_y0 = r_x1 - (w_k + inner * 2), r_y1 - (h_k + inner * 2)
        draw.rectangle([r_x0, r_y0, r_x1, r_y1], outline=(200, 0, 0, 200), width=6)
        draw.text((r_x0 + inner - k_l, r_y0 + inner - k_t), text_k, fill=(200, 0, 0, 200), font=font_stamp)

        # 合成してメモリに保存
        out = Image.alpha_composite(img, txt_layer)
        output = BytesIO()
        out.convert("RGB").save(output, "JPEG", quality=90, optimize=True)
        output.seek(0)
        return output

    def save(self, *args, **kwargs):
        add_watermark = kwargs.pop('add_watermark', True)
        
        # 新規作成時 + 画像が指定されてる時のみ ImageKit にアップロード
        if self.pk is None and self.image:
            try:
                from config.storage import upload_to_imagekit
                
                # メモリ上で画像処理
                processed = self._process_image_in_memory(self.image, add_watermark=add_watermark)
                
                # ImageKitへアップロード
                file_name = os.path.splitext(self.image.name)[0] + '.jpg'
                result = upload_to_imagekit(
                    file=processed,
                    file_name=file_name,
                    folder='products',
                )
                
                if result:
                    self.image_url = result['url']
                    self.imagekit_file_id = result['file_id']
                    print(f"ImageKit upload success: {result['file_id']}")
                else:
                    print("ImageKit upload failed")
                
                # ImageField はもう使わないのでクリア
                self.image = None
                
            except Exception as e:
                print(f"Image processing/upload error: {e}")
        
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # シグナル(pre_delete)で削除されるので、ここでは super().delete() のみ
        super().delete(*args, **kwargs)

    @property
    def optimized_image_url(self):
        """テンプレート用の最適化URL（f-auto, q-auto 付与）"""
        from config.storage import get_optimized_url
        return get_optimized_url(self.image_url)


# --- ImageKit 削除のシグナル ---
# senderを指定しない汎用シグナル(プロキシモデル経由の削除でも発火する)
@receiver(pre_delete)
def delete_imagekit_image(sender, instance, **kwargs):
    """商品削除時にImageKitからも画像を削除（個別・一括・proxy model 全対応）"""
    if hasattr(instance, 'imagekit_file_id') and instance.imagekit_file_id:
        try:
            from config.storage import delete_from_imagekit
            delete_from_imagekit(instance.imagekit_file_id)
            print(f'[ImageKit] Deleted file: {instance.imagekit_file_id}')
        except Exception as e:
            print(f'[ImageKit] Delete signal error: {e}')


# --- 売上記録モデル ---
class Sale(models.Model):
    product_name = models.CharField('商品名', max_length=255)
    price = models.IntegerField('売上金額')
    category = models.CharField('種別', max_length=50, blank=True)
    buyer_name = models.CharField('購入者名', max_length=100, blank=True, default='')
    order_number = models.CharField('注文番号', max_length=20, blank=True, default='')
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


# --- 注文管理モデル ---
class OrderManagement(models.Model):
    order_number = models.CharField('注文番号', max_length=20, unique=True)
    buyer_name = models.CharField('購入者名', max_length=100, blank=True, default='')
    total_price = models.IntegerField('合計金額', default=0)
    product_names = models.TextField('商品名リスト', blank=True, default='')
    sold_at = models.DateTimeField('注文日時')
    yahoo_url = models.URLField('ヤフオクURL', blank=True, default='')
    platform = models.CharField('プラットフォーム', max_length=20, blank=True, default='メルカリ')
    check_listed = models.BooleanField('ヤフオク出品済み', default=False)
    check_sold = models.BooleanField('落札確認', default=False)
    check_shipped = models.BooleanField('発送済み', default=False)

    class Meta:
        verbose_name = '注文管理'
        verbose_name_plural = '注文管理'
        ordering = ['-sold_at']

    def __str__(self):
        return f"{self.order_number} - {self.buyer_name}"

    @property
    def is_completed(self):
        return self.check_listed and self.check_sold and self.check_shipped


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

import os
import json
import random
import re
from datetime import datetime
from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from django import forms
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.apps import apps
from django.template.loader import render_to_string
from .models import Product, Show_ProductList_A4, Z_Archive_A4, Show_ProductList_TCG, Z_Archive_TCG, Sale, OrderManagement

# ✨ 共通CSS定義
COMMON_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rounded+Mplus+1c:wght@700;900&display=swap');
    body, #header, #content, #nav-sidebar, h1, h2, h3, .module caption { font-family: 'Rounded Mplus 1c', sans-serif !important; }
    
    .messagelist { background: none !important; border: none !important; box-shadow: none !important; padding: 0 !important; margin: 0 !important; }
    .messagelist li { background: none !important; border: none !important; padding: 0 !important; color: transparent !important; margin-bottom: 0 !important; }
    .messagelist li > div { color: initial !important; }

    #header { background: #1a1c23 !important; padding: 15px 25px !important; border-bottom: 4px solid transparent !important; border-image: linear-gradient(to right, #ff4d94, #2684ff, #f0ad4e) 1 !important; position: sticky !important; top: 0 !important; z-index: 1000 !important; }
    #branding h1 { font-size: 28px !important; font-weight: 900 !important; display: flex !important; align-items: center !important; justify-content: center !important; gap: 12px !important; background: linear-gradient(to right, #ff69b4, #2684ff, #f0ad4e) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; }
    #branding h1::before { content: none !important; display: none !important; }
    #branding h1 a { color: inherit !important; text-decoration: none !important; }
    
    .app-catalog_pedia caption, .app-catalog_pedia h2, .pedia-mode h2, .pedia-mode caption { background: #6f42c1 !important; color: #fff !important; }
    .app-catalog_a4 caption, .app-catalog_a4 h2 { background: #ff4d94 !important; color: #fff !important; }
    .app-catalog_tcg caption, .app-catalog_tcg h2 { background: #2684ff !important; color: #fff !important; }
    .app-catalog_admin_custom caption, .app-catalog_admin_custom h2, .admin-custom-mode h2, .admin-custom-mode caption, .admin-custom-mode .period-title { background: #f0ad4e !important; color: #fff !important; }

    .home-tile-bg {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        display: grid; 
        grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
        gap: 0px; padding: 0; z-index: 0; opacity: 0.22; pointer-events: none; overflow: hidden; filter: blur(0.5px);
    }
    .home-tile-bg img { width: 100%; height: 160px; object-fit: cover; border-radius: 0px; }
    #container { height: auto !important; overflow: visible !important; }
    .results { overflow: visible !important; }
    #content { position: relative; z-index: 1; background: rgba(18, 18, 18, 0.85) !important; margin: 20px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    #content-main { padding: 0 !important; }
    .changelist-form-container { padding: 0 !important; }
    #changelist.module { padding: 0 !important; margin: 0 !important; border: none !important; }
    #changelist-form { padding: 0 !important; }
    #content-main > * { padding-left: 0 !important; padding-right: 0 !important; }
    #changelist { margin: 0 !important; }
    .dashboard #content { background: rgba(18, 18, 18, 0.7) !important; }
    #header #user-tools a:not([href*="logout"]) { display: none !important; }
    #header #user-tools .divider { display: none !important; }
    #header #user-tools { font-size: 0 !important; }
    #header #user-tools strong, #header #user-tools form, #header #user-tools a[href*="logout"] { font-size: 13px !important; }
    #nav-sidebar .module caption a, #content-main .module caption a.section { pointer-events: none !important; cursor: default !important; text-decoration: none !important; color: inherit !important; }
    .breadcrumbs a:not([href="/admin/"]) { pointer-events: none !important; cursor: default !important; text-decoration: none !important; color: #aaa !important; }
    .breadcrumbs a:not([href="/admin/"]) { pointer-events: none !important; cursor: default !important; text-decoration: none !important; color: #ccc !important; }
    .breadcrumbs { position: sticky !important; top: 75px !important; z-index: 999 !important; background: #1a1c23 !important; }
    .breadcrumbs { background: #1a1c23 !important; color: #ccc !important; }
    .breadcrumbs a { color: #aaa !important; }
    @media (max-width: 768px) {
        #header { padding: 10px 15px !important; text-align: center !important; position: sticky !important; top: 0 !important; z-index: 2000 !important; }
        #branding h1 { justify-content: center !important; font-size: 22px !important; }
        #branding h1 a { justify-content: center !important; }
        .breadcrumbs { position: sticky !important; top: 50px !important; z-index: 590 !important; background: #1a1c23 !important; }
    }
</style>
<script>
    if (location.pathname.includes('character-pedia')) {{
        document.body.classList.add('app-catalog_pedia');
    }}
</script>
<style>
</style>
"""

class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.ImageField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'multiple': True}))
        super().__init__(*args, **kwargs)
    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class BulkUploadForm(forms.Form):
    category = forms.ChoiceField(choices=[('A4', 'A4サイズポスター'), ('TCG', 'トレーディングカード')], label='種別')
    price = forms.IntegerField(label='一括設定金額', initial=88)
    duration_days = forms.ChoiceField(
        choices=[(str(i), f'{i}日間') for i in range(1, 15)],
        label='掲載日数',
        initial='6'
    )
    add_watermark = forms.BooleanField(label='SAMPLEの透かしを追加', required=False, initial=True)
    images = MultipleFileField(label='画像ファイル選択')

class BaseProductAdmin(admin.ModelAdmin):
    list_display = ('display_name_jp', 'display_image_jp', 'display_price_jp', 'display_timer_jp')
    list_display_links = None 
    search_fields = ('name',)
    actions = ['move_to_archive', 'restore_from_archive']
    ordering = ['created_at']

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.username == 'kawaii-girlgallery'

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.username == 'kawaii-girlgallery'

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def get_changelist_instance(self, request):
        # xsortを保存してからGETを除去（get_querysetで使う）
        request._xsort_val = request.GET.get('xsort', '')
        if 'xsort' in request.GET:
            request.GET = request.GET.copy()
            request.GET.pop('xsort')
        return super().get_changelist_instance(request)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            actions['delete_selected'] = (actions['delete_selected'][0], actions['delete_selected'][1], "✅ 選択した商品を削除")
        is_admin = request.user.is_superuser or request.user.username == 'kawaii-girlgallery'
        is_archive_page = 'Archive' in self.__class__.__name__
        if is_archive_page:
            if 'move_to_archive' in actions: del actions['move_to_archive']
        else:
            if 'restore_from_archive' in actions: del actions['restore_from_archive']
        # 管理者以外は保管庫移動・削除を禁止（チェックボックス表示のためdummy actionを残す）
        if not is_admin:
            if 'move_to_archive' in actions: del actions['move_to_archive']
            if 'restore_from_archive' in actions: del actions['restore_from_archive']
            if 'delete_selected' in actions: del actions['delete_selected']
            actions['dummy_action'] = (lambda modeladmin, request, queryset: None, 'dummy_action', '----------')
        return actions

    def get_urls(self):
        return [
            path('bulk-upload/', self.admin_site.admin_view(self.bulk_upload), name='bulk_upload'),
            path('bulk-upload-single/', self.admin_site.admin_view(self.bulk_upload_single), name='bulk_upload_single'),
        ] + super().get_urls()

    def bulk_upload_single(self, request):
        """1枚ずつAjaxでアップロードするエンドポイント"""
        if not (request.user.is_superuser or request.user.username == 'kawaii-girlgallery'):
            return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)
        if request.method != 'POST':
            return JsonResponse({'status': 'error'}, status=405)
        try:
            import re as re_mod
            cat = request.POST.get('category', 'A4')
            pr = int(request.POST.get('price', 88))
            add_watermark = request.POST.get('add_watermark', 'true') == 'true'
            duration_days = int(request.POST.get('duration_days', 6))
            f = request.FILES.get('image')
            if not f:
                return JsonResponse({'status': 'error', 'message': 'ファイルがありません'}, status=400)
            raw_name = os.path.splitext(f.name)[0]
            g_match = re_mod.search(r'(G\d+)$', raw_name, re_mod.IGNORECASE)
            g_number = g_match.group(1) if g_match else None
            base_name = raw_name[:g_match.start()] if g_match else raw_name
            parts = re_mod.split(r'[ _　]', base_name)
            name_parts = []
            for part in parts:
                if '同人' in part: break
                if part: name_parts.append(part)
            if g_number: name_parts.append(g_number)
            product_name = ' '.join(name_parts)
            product = Product(name=product_name, category=cat, price=pr, image=f, duration_days=duration_days)
            product.save(add_watermark=add_watermark)
            return JsonResponse({'status': 'success', 'name': product_name})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    def bulk_upload(self, request):
        if not (request.user.is_superuser or request.user.username == 'kawaii-girlgallery'): return redirect('..')
        return render(request, 'admin/catalog/bulk_upload.html', {
            **self.admin_site.each_context(request),
            'form': BulkUploadForm(initial={'category': 'A4' if 'a4' in request.path else 'TCG', 'add_watermark': True}),
            'title': '一括アップロード'
        })

    def display_name_jp(self, obj):
        import re as re_mod
        parts = obj.name.split(' ')
        if len(parts) >= 2:
            last = parts[-1]
            if re_mod.match(r'^G\d+$', last, re_mod.IGNORECASE):
                middle = '<br>'.join(parts[1:-1]) if len(parts) > 2 else parts[1] if len(parts) > 1 else ''
                return format_html(
                    '<div class="cell-center" style="font-weight: 800; text-align:center;">{}<br>{}<br><span style="color:#aaa;font-size:12px;">{}</span></div>',
                    parts[0], mark_safe(middle), last
                )
        return format_html('<div class="cell-center" style="font-weight: 800; text-align:center;">{}</div>', obj.name)
    display_name_jp.short_description = '商品名'
    def display_image_jp(self, obj):
        if not obj.image: return "なし"
        return format_html('<div class="cell-center" oncontextmenu="return false;"><img src="{}" style="max-height:150px;max-width:150px;border:3px solid #444; border-radius:10px; user-select:none; -webkit-user-drag:none; pointer-events:none;" draggable="false"></div>', obj.image.url)
    display_image_jp.short_description = '画像'
    def display_price_jp(self, obj): return format_html('<div class="cell-center" style="font-weight: 900; color: #00ffcc;">¥{}</div>', obj.price)
    display_price_jp.short_description = '価格'
    def display_timer_jp(self, obj): return format_html('<div class="cell-center"><div class="timer-display" data-date="{}" data-duration="{}" style="font-weight: 800;">⏳ ...</div></div>', obj.created_at.isoformat(), obj.duration_days)
    display_timer_jp.short_description = '掲載期限'
    display_timer_jp.admin_order_field = 'created_at'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        is_archive = 'Archive' in self.__class__.__name__
        # xsortをGETから除去せずget_querysetで使う
        xsort = request.GET.get('xsort', '')

        # ✨ 期限切れ商品を自動アーカイブ
        if not is_archive:
            import datetime
            from django.utils import timezone as tz
            now = tz.now()
            expired = []
            for p in Product.objects.filter(is_archived=False):
                deadline = p.created_at + datetime.timedelta(days=p.duration_days)
                deadline = deadline.replace(hour=23, minute=59, second=59)
                if now > deadline:
                    expired.append(p.id)
            if expired:
                Product.objects.filter(id__in=expired).update(is_archived=True)
        app_config = apps.get_app_config('catalog')
        if "a4" in self.__class__.__name__.lower():
            cat_filter = 'A4'
            app_config.verbose_name = "A4サイズポスター"
        else:
            cat_filter = 'TCG'
            app_config.verbose_name = "トレーディングカード"
        extra_context['title'] = "保管庫" if is_archive else "商品一覧"
        
        self.ordering = ['created_at']

        cl = self.get_changelist_instance(request)
        from django.contrib.admin.templatetags.admin_list import pagination as pagination_tag
        pag_context = pagination_tag(cl)
        pagination_html = format_html('<div class="top-paginator">{}</div>', render_to_string('admin/pagination.html', pag_context))
        
        char_counts, work_counts = {}, {}
        full_qs = Product.objects.filter(category=cat_filter, is_archived=is_archive)
        
        for p in full_qs:
            parts = re.split(r'[ _　]', p.name)
            char_name = parts[0] if parts else "不明"
            char_name = re.sub(r'【.*?】', '', char_name).strip()
            if not char_name:
                char_name = re.sub(r'【.*?】', '', parts[1]).strip() if len(parts) > 1 else "不明"
            if char_name:
                char_counts[char_name] = char_counts.get(char_name, 0) + 1
            
            if len(parts) > 1:
                work_parts = []
                for part in parts[1:]:
                    if "同人" in part: break
                    if re.match(r'^G\d+$', part, re.IGNORECASE): break
                    work_parts.append(part)
                work_name = " ".join(work_parts).strip() if work_parts else "単体作品"
                if work_name:
                    work_counts[work_name] = work_counts.get(work_name, 0) + 1
        
        current_query = request.GET.get('q')
        back_btn_html = f'<a href="." style="text-decoration:none; margin-left:10px;"><div style="background:#ff4444; border:2px solid #ff6666; padding:4px 15px; border-radius:20px; color:#fff; font-size:12px; font-weight:900; display:inline-block;">⬅ 戻る</div></a>' if current_query else ""

        def make_btns(data, color, panel_id):
            sorted_data = sorted(data.items(), key=lambda x: x[0])
            return "".join([format_html(
                '<a href="?q={}" onclick="closePanel(\'{}\');" style="text-decoration:none; display:inline-block; margin-bottom:6px;"><div style="background:#222; border:2px solid {}; padding:4px 10px; border-radius:20px; color:#fff; font-size:11px; font-weight:800;">{} <span style="color:#00ffcc;">({})</span></div></a>',
                n, panel_id, "#00ffcc" if current_query == n else color, n, c
            ) for n, c in sorted_data])

        char_btns = make_btns(char_counts, "#ff69b4", "char-panel")
        work_btns = make_btns(work_counts, "#007bff", "work-panel")

        is_admin_flag = 'true' if (request.user.is_superuser or request.user.username == 'kawaii-girlgallery') else 'false'

        accordion_html = mark_safe(f'''
<style>
    .qs-tab-wrap {{
        position: fixed;
        right: 0;
        top: 50%;
        transform: translateY(-50%);
        display: flex;
        flex-direction: column;
        gap: 8px;
        z-index: 3000;
    }}
    .qs-tab {{
        writing-mode: vertical-rl;
        text-orientation: mixed;
        padding: 16px 8px;
        border-radius: 10px 0 0 10px;
        font-size: 12px;
        font-weight: 900;
        cursor: pointer;
        color: #fff;
        user-select: none;
        letter-spacing: 1px;
        border: 2px solid transparent;
        border-right: none;
        transition: opacity 0.2s;
    }}
    .qs-tab:hover {{ opacity: 0.85; }}
    .qs-tab-char {{ background: #ff69b4; border-color: #ff69b4; }}
    .qs-tab-work {{ background: #007bff; border-color: #007bff; }}
    .qs-panel {{
        position: fixed;
        right: -420px;
        top: 0;
        width: 400px;
        height: 100vh;
        background: #111;
        z-index: 2999;
        display: flex;
        flex-direction: column;
        transition: right 0.3s ease;
        box-shadow: -4px 0 20px rgba(0,0,0,0.7);
    }}
    .qs-panel.open {{ right: 0; }}
    .qs-panel-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px;
        border-bottom: 2px solid #333;
        flex-shrink: 0;
    }}
    .qs-panel-title {{
        font-size: 15px;
        font-weight: 900;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .qs-panel-close {{
        background: #222;
        border: 1px solid #444;
        border-radius: 50%;
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: #aaa;
        font-size: 14px;
        font-weight: 900;
    }}
    .qs-panel-close:hover {{ background: #333; color: #fff; }}
    .qs-panel-body {{
        flex: 1;
        overflow-y: auto;
        padding: 14px;
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        align-content: flex-start;
    }}
    .qs-panel-body::-webkit-scrollbar {{ width: 6px; }}
    .qs-panel-body::-webkit-scrollbar-track {{ background: #1a1a1a; }}
    .qs-panel-body::-webkit-scrollbar-thumb {{ background: #444; border-radius: 3px; }}
    .messagelist {{ display: none !important; }}
    .top-paginator {{ display: none !important; }}
</style>

<div class="qs-tab-wrap">
    <div class="qs-tab qs-tab-char" onclick="togglePanel('char-panel')">👤 キャラクター検索</div>
    <div class="qs-tab qs-tab-work" onclick="togglePanel('work-panel')">🎬 原作作品検索</div>
</div>

<div id="char-panel" class="qs-panel" style="border-left: 3px solid #ff69b4;">
    <div class="qs-panel-header">
        <div class="qs-panel-title" style="color: #ff69b4;">👤 キャラクター検索 {back_btn_html}</div>
        <div class="qs-panel-close" onclick="closePanel('char-panel')">✕</div>
    </div>
    <div class="qs-panel-body">{char_btns}</div>
</div>

<div id="work-panel" class="qs-panel" style="border-left: 3px solid #007bff;">
    <div class="qs-panel-header">
        <div class="qs-panel-title" style="color: #007bff;">🎬 原作作品検索</div>
        <div class="qs-panel-close" onclick="closePanel('work-panel')">✕</div>
    </div>
    <div class="qs-panel-body">{work_btns}</div>
</div>

<script>
function togglePanel(id) {{
    var panel = document.getElementById(id);
    if (panel.classList.contains('open')) {{
        panel.classList.remove('open');
    }} else {{
        panel.classList.add('open');
    }}
}}
function closePanel(id) {{
    var panel = document.getElementById(id);
    if (panel) panel.classList.remove('open');
}}
</script>
''')

        custom_css = f"""<style>
            #result_list tbody td {{ text-align: center !important; vertical-align: middle !important; padding: 12px 5px !important; font-weight: 700; }}
            #result_list thead {{ display: none !important; }}
            .cell-center {{ display: flex; flex-direction: column; align-items: center; justify-content: center; height: 170px; width: 100%; }}
            .cell-center img {{ pointer-events: none !important; user-select: none !important; -webkit-user-drag: none !important; }}
            .cell-center img {{ -webkit-user-drag: none; user-select: none; -moz-user-select: none; }}

            #content h1 {{ display: none !important; }}
            img {{ -webkit-user-drag: none !important; user-select: none !important; }}
            #result_list img {{ pointer-events: none !important; }}

            #changelist-search {{ display: none !important; }}
            .object-tools {{ display: none !important; }}
            #changelist .actions {{ display: none !important; }}
            #toolbar {{ display: none !important; }}
            #changelist .actions + p,
            #changelist > div:has(> .actions),
            .changelist-form-wrapper > div:empty,
            #changelist hr,
            #changelist p.paginator {{ display: none !important; }}
            #changelist > div {{ background: none !important; border: none !important; box-shadow: none !important; padding: 0 !important; margin: 0 !important; }}
            #changelist-form > p {{ display: none !important; }}
            .top-paginator {{ display: none !important; }}
            #changelist .paginator {{ display: none !important; }}

            .smart-top-bar {{
                display: flex;
                align-items: center;
                gap: 6px;
                background: #1a1a1a !important;
                padding: 8px 12px;
                border-radius: 10px;
                margin-bottom: 4px;
                flex-wrap: nowrap;
                box-sizing: border-box;
            }}
            .smart-search-form {{ display: flex; align-items: center; gap: 6px; flex-shrink: 0; }}
            .smart-search-form input[type=text] {{
                background: #2a2a2a; border: 1px solid #555; color: #fff;
                border-radius: 8px; padding: 5px 8px; font-size: 12px; font-weight: 700; width: 100px;
            }}
            .smart-search-form input[type=submit] {{
                background: #333; border: 1px solid #555; color: #fff;
                border-radius: 8px; padding: 5px 12px; font-size: 12px; font-weight: 900; cursor: pointer;
            }}
            .smart-paginator {{ display: flex; align-items: center; gap: 2px; flex-shrink: 1; flex-wrap: nowrap; }}
            .smart-paginator a, .smart-paginator span.this-page {{
                display: inline-flex !important; align-items: center; justify-content: center;
                min-width: 22px; height: 22px; padding: 0 4px;
                background: #2a2a2a; border: 1px solid #444; border-radius: 4px;
                color: #00ffcc !important; font-weight: 900; font-size: 11px; text-decoration: none;
            }}
            .smart-paginator span.this-page {{
                background: #007bff; border-color: #007bff; color: #fff !important;
            }}
            .smart-paginator .total-count {{
                color: #aaa; font-size: 11px; font-weight: 700; white-space: nowrap; margin-left: 4px;
            }}
            .smart-top-bar-spacer {{ flex: 1; }}
            .smart-btn-group {{ display: flex; align-items: center; gap: 8px; flex-shrink: 0; }}

            .smart-action-bar {{
                display: flex;
                align-items: center;
                gap: 10px;
                background: #1a1a1a;
                padding: 8px 15px;
                border-radius: 10px;
                margin-bottom: 15px;
                flex-wrap: wrap;
                box-sizing: border-box;
            }}
            .smart-action-bar select {{
                background: #2a2a2a; border: 1px solid #555; color: #fff;
                border-radius: 8px; padding: 5px 10px; font-size: 13px; font-weight: 700;
            }}
            .smart-action-bar .run-btn {{
                background: #333; border: 1px solid #555; color: #fff;
                border-radius: 8px; padding: 5px 14px; font-size: 12px; font-weight: 900; cursor: pointer;
            }}
            .smart-action-bar .counter-label {{
                color: #aaa; font-size: 12px; font-weight: 700;
            }}

            /* カートタブ（PC・スマホ共通） */
            .sp-cart-tab {{
                position: fixed !important;
                right: 0 !important;
                top: 72% !important;
                z-index: 3100 !important;
                writing-mode: vertical-rl !important;
                text-orientation: mixed !important;
                padding: 16px 8px !important;
                min-height: 130px !important;
                background: #28a745 !important;
                color: #fff !important;
                font-size: 12px !important;
                font-weight: 900 !important;
                border-radius: 10px 0 0 10px !important;
                cursor: pointer !important;
                user-select: none !important;
                letter-spacing: 1px !important;
                border: 2px solid #28a745 !important;
                border-right: none !important;
                display: none !important;
                align-items: center !important;
                justify-content: center !important;
            }}
            .sp-cart-tab.visible {{
                display: flex !important;
            }}
            /* カート内画像の保存禁止 */
            #cart-popup img {{
                pointer-events: none !important;
                user-select: none !important;
                -webkit-user-drag: none !important;
                -webkit-touch-callout: none !important;
            }}
            /* 閉じるボタンはPC・スマホ共通で表示 */
            /* PCではcart-popupを右下固定表示（スマホのアコーディオンをリセット） */
            @media (min-width: 769px) {{
                #cart-popup {{
                    position: fixed !important;
                    right: 20px !important;
                    bottom: 20px !important;
                    top: auto !important;
                    width: 280px !important;
                    max-height: none !important;
                    border-radius: 10px !important;
                    border: 1px solid #444 !important;
                    transition: none !important;
                    z-index: 9999 !important;
                }}
                /* PCでもカートタブを表示 */
                .sp-cart-tab {{
                    display: none;
                }}
                .sp-cart-tab.visible {{
                    display: flex !important;
                }}
            }}

            #pos-modal {{ background-color: rgba(0, 0, 0, 0.98) !important; display: none; position: fixed !important; z-index: 20000 !important; top: 0; left: 0; width: 100vw; height: 100vh; }}
            .modal-nav {{ position: fixed !important; top: 50% !important; transform: translateY(-50%) !important; font-size: 80px !important; color: rgba(255,255,255,0.4) !important; z-index: 20020 !important; cursor: pointer; padding: 20px; }}
            .nav-prev {{ left: 2vw !important; }} .nav-next {{ right: 2vw !important; }}
            @media (max-width: 768px) {{
                .modal-content {{ max-height: 60vh !important; max-width: 60vw !important; }}
                .modal-nav {{ font-size: 50px !important; color: rgba(255,255,255,0.9) !important; background: rgba(0,0,0,0.5) !important; border-radius: 50% !important; width: 50px !important; height: 50px !important; display: flex !important; align-items: center !important; justify-content: center !important; padding: 0 !important; }}
                .nav-prev {{ left: 4px !important; }} .nav-next {{ right: 4px !important; }}
            }}
            .modal-center-container {{ display: flex !important; justify-content: center !important; align-items: center !important; height: 100vh !important; width: 100vw !important; }}
            .modal-main-unit {{ display: flex !important; flex-direction: column !important; align-items: center !important; }}
            .modal-content {{ max-height: 70vh !important; max-width: 80vw !important; border: 3px solid #fff !important; border-radius: 0 !important; display: block !important; }}
            #modal-add-btn {{ position: fixed !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 40px !important; background: rgba(40, 167, 69, 0.9) !important; color: white !important; font-size: 15px !important; font-weight: 900 !important; border: none !important; border-bottom: 2px solid #fff !important; z-index: 21000 !important; display: flex !important; align-items: center !important; justify-content: center !important; cursor: pointer !important; }}
            .close-btn {{ position: fixed !important; top: 50px !important; right: 30px !important; color: #fff !important; font-size: 50px !important; z-index: 21100 !important; cursor: pointer; }}

            /* ============================================================
               ✨ スマホ専用カードレイアウト（768px以下のみ / PCは変わりません）
               ============================================================ */
            @media (max-width: 768px) {{
                #result_list thead {{ display: none !important; }}
                #result_list tbody tr {{
                    display: block !important; position: relative !important;
                    background: #1e1e1e !important; border: 1px solid #333 !important;
                    border-radius: 12px !important; margin: 8px !important;
                    padding: 12px 8px 12px 44px !important;
                    width: calc(100% - 16px) !important; box-sizing: border-box !important;
                }}
                #result_list tbody td {{
                    display: block !important; width: 100% !important;
                    text-align: center !important; padding: 4px 8px !important;
                    border: none !important; height: auto !important;
                }}
                #result_list tbody td.action-checkbox {{
                    position: absolute !important; left: 10px !important;
                    top: 50% !important; transform: translateY(-50%) !important;
                    width: 28px !important; padding: 0 !important;
                    display: flex !important; align-items: center !important; justify-content: center !important;
                }}
                #result_list tbody td.action-checkbox input {{ width: 22px !important; height: 22px !important; margin: 0 !important; }}
                .cell-center {{ height: auto !important; min-height: 0 !important; padding: 4px 0 !important; }}
                #result_list tbody td .cell-center img {{ max-height: 200px !important; max-width: 85vw !important; }}
                #result_list tbody tr:nth-child(even) {{ background: #222 !important; }}
                .smart-top-bar {{ flex-wrap: wrap !important; padding: 8px 10px !important; background: #1a1a1a !important; }}
                .smart-top-bar[style*="fixed"] {{ background: #1a1a1a !important; }}
                .smart-search-form {{ flex: 1 1 auto !important; }}
                .smart-search-form input[type=text] {{ width: 100% !important; font-size: 15px !important; padding: 8px 12px !important; }}
                .smart-search-form input[type=submit] {{ padding: 8px 14px !important; min-height: 38px !important; }}
                .smart-paginator {{ order: 3 !important; width: 100% !important; flex-wrap: wrap !important; }}
                .smart-paginator a, .smart-paginator span.this-page {{ min-width: 38px !important; height: 38px !important; }}
                .smart-top-bar-spacer {{ display: none !important; }}
                .smart-btn-group {{ order: 4 !important; width: 100% !important; flex-wrap: wrap !important; gap: 6px !important; }}
                .smart-btn-group a {{ flex: 0 0 auto !important; justify-content: center !important; font-size: 11px !important; padding: 6px 12px !important; min-height: 32px !important; display: inline-flex !important; align-items: center !important; border-radius: 16px !important; }}
                .smart-action-bar {{ padding: 8px 10px !important; }}
                .smart-action-bar select {{ flex: 1 1 auto !important; min-height: 38px !important; }}
                .smart-action-bar .run-btn {{ min-height: 38px !important; padding: 8px 18px !important; }}

                /* ✨ スマホ×非管理者：操作UIを非表示 */
                .sp-hide-mobile {{
                    display: none !important;
                }}
                /* 閉じるボタンはスマホのみ表示 */
                .sp-cart-close-btn {{ display: block !important; }}

                /* カート×ボタンを大きく */
                #cart-popup button[onclick*="removeFromCart"] {{
                    font-size: 24px !important;
                    width: 36px !important;
                    height: 36px !important;
                    padding: 0 !important;
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                    flex-shrink: 0 !important;
                }}

                /* ✨ スマホ時：#cart-popup をアコーディオンタブに収納 */
                #cart-popup {{
                    position: fixed !important;
                    right: -100vw !important;
                    bottom: 0 !important;
                    top: auto !important;
                    width: min(260px, 80vw) !important;
                    max-height: 45vh !important;
                    overflow-y: auto !important;
                    border-radius: 12px 0 0 0 !important;
                    border-left: 3px solid #28a745 !important;
                    border-top: 3px solid #28a745 !important;
                    transition: right 0.3s ease !important;
                    z-index: 3099 !important;
                    box-shadow: -4px 0 20px rgba(0,0,0,0.7) !important;
                }}
                #cart-popup.sp-open {{
                    right: 0 !important;
                }}
                /* sp-cart-tabはPC共通CSSで定義 */
                /* カート追加トースト */
                .sp-cart-toast {{
                    position: fixed !important;
                    bottom: 80px !important;
                    left: 50% !important;
                    transform: translateX(-50%) translateY(20px) !important;
                    background: #28a745 !important;
                    color: #fff !important;
                    font-size: 13px !important;
                    font-weight: 900 !important;
                    padding: 10px 20px !important;
                    border-radius: 20px !important;
                    z-index: 9999 !important;
                    opacity: 0 !important;
                    transition: opacity 0.2s, transform 0.2s !important;
                    pointer-events: none !important;
                    white-space: nowrap !important;
                }}
                .sp-cart-toast.show {{
                    opacity: 1 !important;
                    transform: translateX(-50%) translateY(0) !important;
                }}
            }}
        </style>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var tabWrap = document.querySelector(".qs-tab-wrap");
                var charPanel = document.getElementById("char-panel");
                var workPanel = document.getElementById("work-panel");
                if (tabWrap) document.body.appendChild(tabWrap);
                if (charPanel) document.body.appendChild(charPanel);
                if (workPanel) document.body.appendChild(workPanel);

                var changelist = document.querySelector('#changelist');
                if (!changelist) return;

                var origSearchInput = document.querySelector('#searchbar');
                var origPaginator = document.querySelector('#changelist .paginator');
                var origActions = document.querySelector('#changelist .actions');

                // smart-top-barが既存なら挿入スキップ（アコーディオン・カートは毎回実行）
                var skipTopBar = !!document.querySelector(".smart-top-bar");
                var topBar = skipTopBar ? document.querySelector(".smart-top-bar") : document.createElement("div");
                if (!skipTopBar) topBar.className = 'smart-top-bar';

                var searchForm = document.createElement('form');
                searchForm.method = 'GET';
                searchForm.className = 'smart-search-form';
                var sInput = document.createElement('input');
                sInput.type = 'text';
                sInput.name = 'q';
                sInput.placeholder = '🔍 検索...';
                sInput.value = origSearchInput ? origSearchInput.value : '';
                var sSubmit = document.createElement('input');
                sSubmit.type = 'submit';
                sSubmit.value = '検索';
                searchForm.appendChild(sInput);
                searchForm.appendChild(sSubmit);
                topBar.appendChild(searchForm);

                if (origPaginator) {{
                    var pagDiv = document.createElement("div");
                    pagDiv.className = 'smart-paginator';
                    var lis = origPaginator.querySelectorAll('li');
                    
                    // ページ番号を収集
                    var pages = [];
                    if (lis.length > 0) {{
                        lis.forEach(function(li) {{
                            var a = li.querySelector('a');
                            var s = li.querySelector('span.this-page');
                            if (a) pages.push({{ type: 'a', href: a.href, text: a.textContent.trim() }});
                            else if (s) pages.push({{ type: 'current', text: s.textContent.trim() }});
                        }});
                    }} else {{
                        origPaginator.querySelectorAll('a').forEach(function(a) {{
                            pages.push({{ type: 'a', href: a.href, text: a.textContent.trim() }});
                        }});
                    }}

                    // スマホ時は5ページ以上を省略
                    var isMobileForPag = window.innerWidth <= 768;
                    var currentIdx = pages.findIndex(function(p) {{ return p.type === 'current'; }});
                    
                    pages.forEach(function(p, i) {{
                        // スマホで6ページ以上の場合：現在ページ±2と最初2件・最後2件を表示
                        if (isMobileForPag && pages.length > 5) {{
                            var isFirst2 = i <= 1;
                            var isLast2 = i >= pages.length - 2;
                            var isNearCurrent = Math.abs(i - currentIdx) <= 2;
                            if (!isFirst2 && !isLast2 && !isNearCurrent) {{
                                // 省略記号を追加（隣接する省略は1つだけ）
                                if (pagDiv.lastChild && pagDiv.lastChild.textContent !== '…') {{
                                    var dots = document.createElement('span');
                                    dots.textContent = '…';
                                    dots.style.cssText = 'color:#aaa; padding: 0 2px;';
                                    pagDiv.appendChild(dots);
                                }}
                                return;
                            }}
                        }}
                        if (p.type === 'a') {{
                            var newA = document.createElement('a');
                            newA.href = p.href;
                            newA.textContent = p.text;
                            pagDiv.appendChild(newA);
                        }} else {{
                            var newS = document.createElement('span');
                            newS.className = 'this-page';
                            newS.textContent = p.text;
                            pagDiv.appendChild(newS);
                        }}
                    }});

                    var totalText = origPaginator.textContent.match(/[0-9]+ *商品一覧/);
                    if (totalText) {{
                        var countSpan = document.createElement('span');
                        countSpan.className = 'total-count';
                        countSpan.textContent = totalText[0];
                        pagDiv.appendChild(countSpan);
                    }}
                    topBar.appendChild(pagDiv);
                }}

                var spacer = document.createElement("div");
                spacer.className = 'smart-top-bar-spacer';
                topBar.appendChild(spacer);

                var btnGroup = document.createElement("div");
                btnGroup.className = 'smart-btn-group';



                var btnSlide = document.createElement('a');
                btnSlide.href = 'javascript:void(0)';
                btnSlide.setAttribute('onclick', 'bulkCarousel()');
                btnSlide.innerHTML = '🎥 スライド拡大確認';
                btnSlide.style.cssText = 'background:#007bff; color:#fff; padding:6px 16px; border-radius:20px; font-weight:900; text-decoration:none; font-size:13px; cursor:pointer;';
                btnGroup.appendChild(btnSlide);

                var btnCart = document.createElement('a');
                btnCart.href = 'javascript:void(0)';
                btnCart.setAttribute('onclick', 'bulkAddToCart()');
                btnCart.innerHTML = '🛒 カートへ追加';
                btnCart.style.cssText = 'background:#28a745; color:#fff; padding:6px 16px; border-radius:20px; font-weight:900; text-decoration:none; font-size:13px; cursor:pointer;';
                btnGroup.appendChild(btnCart);

                topBar.appendChild(btnGroup);

                var actionBar = document.createElement("div");
                actionBar.className = 'smart-action-bar';

                if (origActions) {{
                    var sel = origActions.querySelector('select');
                    if (sel) {{
                        var newSel = sel.cloneNode(true);
                        newSel.addEventListener('change', function() {{ sel.value = this.value; }});
                        actionBar.appendChild(newSel);
                    }}
                    var runBtn = document.createElement('button');
                    runBtn.type = 'button';
                    runBtn.className = 'run-btn';
                    runBtn.textContent = 'Run';
                    runBtn.addEventListener('click', function() {{
                        var newSel = actionBar.querySelector('select');
                        if (sel && newSel) sel.value = newSel.value;
                        var actionForm = origActions.closest('form');
                        if (actionForm) actionForm.submit();
                    }});
                    actionBar.appendChild(runBtn);
                    var counter = origActions.querySelector('.action-counter');
                    if (counter) {{
                        var newCounter = document.createElement('span');
                        newCounter.className = 'counter-label';
                        newCounter.textContent = counter.textContent;
                        actionBar.appendChild(newCounter);
                    }}
                }}
                var actionSpacer = document.createElement("div");
                actionSpacer.style.flex = '1';
                actionBar.appendChild(actionSpacer);

                // ソートドロップダウン
                var sortSel = document.createElement('select');
                sortSel.style.cssText = 'background:#2a2a2a; border:1px solid #555; color:#fff; border-radius:8px; padding:5px 10px; font-size:12px; font-weight:700; cursor:pointer;';
                var currentSort = new URLSearchParams(window.location.search).get('xsort') || '';
                [['', '並び順'], ['asc', '⏳ 期限近い順'], ['desc', '⌛ 期限遠い順']].forEach(function(opt) {{
                    var o = document.createElement('option');
                    o.value = opt[0];
                    o.textContent = opt[1];
                    if (opt[0] === currentSort) o.selected = true;
                    sortSel.appendChild(o);
                }});
                sortSel.addEventListener('change', function() {{
                    var p = new URLSearchParams(window.location.search);
                    if (this.value) {{ p.set('xsort', this.value); }} else {{ p.delete('xsort'); }}
                    p.delete('p');
                    window.location.href = '?' + p.toString();
                }});
                actionBar.appendChild(sortSel);
                if ({is_admin_flag} === true) {{
                    var btnUpload2 = document.createElement('a');
                    btnUpload2.href = 'bulk-upload/';
                    btnUpload2.innerHTML = '📂 一括アップロード ＋';
                    btnUpload2.style.cssText = 'background:#f0ad4e; color:#fff; padding:6px 16px; border-radius:20px; font-weight:900; text-decoration:none; font-size:13px;';
                    actionBar.appendChild(btnUpload2);
                }}

                if (!skipTopBar) changelist.parentNode.insertBefore(actionBar, changelist);

                var header = document.querySelector("#header");
                var breadcrumbs = document.querySelector(".breadcrumbs");
                var navSidebar = document.querySelector("#nav-sidebar");
                var headerH = header ? header.offsetHeight : 75;
                var breadcrumbsH = breadcrumbs ? breadcrumbs.offsetHeight : 41;
                var sidebarW = navSidebar ? navSidebar.offsetWidth : 277;

                var isMobile = window.innerWidth <= 768;
                if (!isMobile && !skipTopBar) {{
                    if (header) {{
                        header.style.cssText += "; position: fixed !important; top: 0 !important; left: 0 !important; right: 0 !important; width: 100% !important; z-index: 2000 !important;";
                    }}
                    if (breadcrumbs) {{
                        document.body.appendChild(breadcrumbs);
                        breadcrumbs.style.cssText = "position: fixed !important; top: " + headerH + "px !important; left: 0 !important; right: 0 !important; width: 100% !important; z-index: 1999 !important; background: #1a1c23 !important; padding: 8px 20px !important; margin: 0 !important;";
                    }}
                    if (navSidebar) {{
                        navSidebar.style.cssText += "; position: fixed !important; top: " + (headerH + breadcrumbsH) + "px !important; left: 0 !important; width: " + sidebarW + "px !important; height: calc(100vh - " + (headerH + breadcrumbsH) + "px) !important; overflow-y: auto !important; z-index: 1500 !important;";
                        var contentWrapper = document.querySelector("#content");
                        if (contentWrapper) contentWrapper.style.marginLeft = sidebarW + "px";
                    }}
                    document.body.style.paddingTop = (headerH + breadcrumbsH) + "px";
                }} else {{
                    // スマホ：marginLeftをリセット
                    var contentWrapper = document.querySelector("#content");
                    if (contentWrapper) contentWrapper.style.marginLeft = "0";
                }}

                var tabWrap2 = document.querySelector(".qs-tab-wrap");
                var charPanel2 = document.querySelector("#char-panel");
                var workPanel2 = document.querySelector("#work-panel");
                if (tabWrap2) document.body.appendChild(tabWrap2);
                if (charPanel2) document.body.appendChild(charPanel2);
                if (workPanel2) document.body.appendChild(workPanel2);

                var selectAllWrap = document.createElement('label');
                selectAllWrap.style.cssText = 'display:flex; align-items:center; gap:6px; cursor:pointer; color:#aaa; font-size:12px; font-weight:900;';
                var selectAllChk = document.createElement('input');
                selectAllChk.type = 'checkbox';
                selectAllChk.style.cssText = 'width:16px; height:16px; cursor:pointer; accent-color:#007bff;';
                selectAllChk.addEventListener('change', function() {{
                    document.querySelectorAll('.action-select').forEach(function(cb) {{
                        cb.checked = selectAllChk.checked;
                    }});
                    var origToggle = document.querySelector('#action-toggle');
                    if (origToggle) origToggle.checked = selectAllChk.checked;
                }});
                var selectAllLabel = document.createElement('span');
                selectAllLabel.textContent = '全選択';
                selectAllWrap.appendChild(selectAllChk);
                selectAllWrap.appendChild(selectAllLabel);
                actionBar.insertBefore(selectAllWrap, actionBar.firstChild);

                if (!skipTopBar) {{
                    changelist.parentNode.insertBefore(actionBar, changelist);
                    changelist.parentNode.insertBefore(topBar, actionBar);
                }}

                var fixedTopVal = header ? header.offsetHeight : 75;
                fixedTopVal += breadcrumbs ? breadcrumbs.offsetHeight : 37;
                var topBarW = topBar.offsetWidth;
                var topBarLeft = topBar.getBoundingClientRect().left;

                // ✨ スマホ×非管理者：検索窓・プルダウン・Runを非表示（チェックボックスは残す）
                if (isMobile && {is_admin_flag} === false) {{
                    // 検索フォームのみ非表示（ページネーターは残す）
                    var sf = topBar ? topBar.querySelector(".smart-search-form") : null;
                    if (sf) sf.classList.add("sp-hide-mobile");
                    // actionBar内のselect・run・counterのみ非表示
                    if (actionBar) {{
                        var sel = actionBar.querySelector("select");
                        var run = actionBar.querySelector(".run-btn");
                        var counter = actionBar.querySelector(".counter-label");
                        var upload = actionBar.querySelector("a[href*='bulk-upload']");
                        if (sel) sel.classList.add("sp-hide-mobile");
                        if (run) run.classList.add("sp-hide-mobile");
                        if (counter) counter.classList.add("sp-hide-mobile");
                        if (upload) upload.classList.add("sp-hide-mobile");
                    }}
                }}

                // ✨ スマホ時：カード内のtd順を 画像→名前→価格→タイマー に並び替え
                if (isMobile) {{
                    document.querySelectorAll("#result_list tbody tr").forEach(function(tr) {{
                        var tdImg = null, tdName = null, tdPrice = null, tdTimer = null;
                        tr.querySelectorAll("td:not(.action-checkbox)").forEach(function(td) {{
                            var inner = td.querySelector(".cell-center");
                            if (!inner) return;
                            if (inner.querySelector("img"))                        tdImg   = td;
                            else if (inner.querySelector(".timer-display"))        tdTimer = td;
                            else if (inner.querySelector("[style*='00ffcc']"))     tdPrice = td;
                            else                                                   tdName  = td;
                        }});
                        [tdImg, tdName, tdPrice, tdTimer].forEach(function(td) {{
                            if (td) tr.appendChild(td);
                        }});
                    }});
                }}

                // ✨ カートタブ（PC・スマホ共通）
                var spCartOpen = false;
                var spCartTab = null;

                    function setupSpCart() {{
                        if (spCartTab) return; // 二重生成防止

                        spCartTab = document.createElement("div");
                        spCartTab.className = "sp-cart-tab";
                        spCartTab.textContent = "カート";
                        document.body.appendChild(spCartTab);

                        spCartTab.addEventListener("click", function() {{
                            var popup = document.getElementById("cart-popup");
                            if (!popup) return;
                            spCartOpen = true;
                            if (isMobile) {{
                                popup.style.display = "block";
                                popup.classList.add("sp-open");
                            }} else {{
                                popup.style.display = "block";
                            }}
                            spCartTab.classList.remove("visible");
                            spCartTab.style.setProperty("display", "none", "important");
                        }});
                    }}

                    // トースト表示関数
                    function showCartToast(msg) {{
                        var existing = document.querySelector(".sp-cart-toast");
                        if (existing) existing.remove();
                        var toast = document.createElement("div");
                        toast.className = "sp-cart-toast";
                        toast.textContent = msg;
                        document.body.appendChild(toast);
                        requestAnimationFrame(function() {{
                            requestAnimationFrame(function() {{
                                toast.classList.add("show");
                                setTimeout(function() {{
                                    toast.classList.remove("show");
                                    setTimeout(function() {{ toast.remove(); }}, 250);
                                }}, 1500);
                            }});
                        }});
                    }}

                    // renderCart後にタブを表示・自動オープンする
                    // pos_system.jsのrenderCartをラップ
                    // カートを閉じるグローバル関数
                    window.spCartCloseFunc = function() {{
                        var popup = document.getElementById("cart-popup");
                        if (popup) {{
                            popup.classList.remove("sp-open");
                            if (!isMobile) popup.style.display = "none";
                        }}
                        spCartOpen = false;
                        if (spCartTab) spCartTab.classList.add("visible");
                    }};

                    function watchCart() {{
                        var popup = document.getElementById("cart-popup");
                        if (!popup) {{
                            setTimeout(watchCart, 200);
                            return;
                        }}
                        setupSpCart();



                        // cart-popupのdisplay・中身の変化を監視
                        var prevCartCount = 0;
                        var styleObserver = new MutationObserver(function() {{
                            var popup = document.getElementById("cart-popup");
                            if (!popup) return;
                            var hasItems = popup.style.display !== "none" && popup.innerHTML.includes("removeFromCart");
                            if (hasItems) {{
                                // カートが閉じている時だけタブを表示
                                if (!spCartOpen) spCartTab.classList.add("visible");
                                // カートの件数を数えて「増えた時だけ」トーストを表示
                                var currentCount = (popup.innerHTML.match(/removeFromCart/g) || []).length;
                                if (currentCount > prevCartCount) {{
                                    showCartToast("🛒 カートに追加しました");
                                }}
                                prevCartCount = currentCount;
                            }} else {{
                                // カートが空の時だけタブを非表示（閉じた時は非表示にしない）
                                var cartIsEmpty = !popup.innerHTML.includes("removeFromCart");
                                if (cartIsEmpty) {{
                                    spCartTab.classList.remove("visible");
                                }}
                                popup.classList.remove("sp-open");
                                spCartOpen = false;
                                spCartTab.style.background = "#28a745";
                                prevCartCount = 0;
                            }}
                        }});
                        styleObserver.observe(popup, {{ childList: true, subtree: false }});

                        // 初期状態確認
                        if (popup.style.display !== "none" && popup.innerHTML.includes("removeFromCart")) {{
                            spCartTab.classList.add("visible");
                        }}
                    }}
                    watchCart();

                // カートタブの初期状態を設定（ページ更新後も正しく表示）
                setTimeout(function() {{
                    var popup = document.getElementById("cart-popup");
                    var tab = document.querySelector(".sp-cart-tab");
                    if (popup && tab) {{
                        var hasItems = popup.style.display !== "none" && popup.innerHTML.includes("removeFromCart");
                        if (hasItems) {{
                            tab.classList.add("visible");
                        }}
                    }}
                }}, 300);

                // theadのtopをボタンバーの高さに合わせて設定
                function updateTheadTop() {{
                    var thead = document.querySelector("#result_list thead");
                    var tb = document.querySelector(".smart-top-bar");
                    var ab = document.querySelector(".smart-action-bar");
                    if (thead && tb && ab) {{
                        var topH = tb.offsetHeight + ab.offsetHeight;
                        thead.style.top = topH + "px";
                    }}
                }}
                updateTheadTop();
                window.addEventListener("resize", updateTheadTop);

                // 初期化時にスクロールイベントを発火して固定状態を設定
                setTimeout(function() {{ window.dispatchEvent(new Event("scroll")); }}, 100);

                window.addEventListener("scroll", function() {{
                    var scrollY = window.scrollY;
                    // 毎回DOMから直接取得
                    var tb = document.querySelector(".smart-top-bar");
                    var ab = document.querySelector(".smart-action-bar");
                    var cd = document.querySelector("#content");
                    if (!tb) return;
                    if (scrollY > 44) {{
                        tb.style.position = "fixed";
                        tb.style.top = fixedTopVal + "px";
                        tb.style.left = topBarLeft + "px";
                        var adjustedW = document.querySelector("#result_list") ? document.querySelector("#result_list").offsetWidth : topBarW;
                        tb.style.width = adjustedW + "px";
                        tb.style.zIndex = "601";
                        tb.style.setProperty("background", "#1a1a1a", "important");
                        tb.style.borderRadius = "0";
                        tb.style.boxShadow = "0 2px 8px rgba(0,0,0,0.9)";
                        if (ab) {{
                            ab.style.position = "fixed";
                            ab.style.top = (fixedTopVal + tb.offsetHeight) + "px";
                            ab.style.left = topBarLeft + "px";
                            ab.style.width = adjustedW + "px";
                            ab.style.zIndex = "600";
                            ab.style.setProperty("background", "#1a1a1a", "important");
                        }}
                        if (cd) {{
                            var pad = tb.offsetHeight + (ab ? ab.offsetHeight : 0);
                            cd.style.marginTop = pad + "px";
                        }}
                        // 固定バー下の背景オーバーレイ
                        var overlay = document.getElementById("sp-bar-overlay");
                        if (!overlay) {{
                            overlay = document.createElement("div");
                            overlay.id = "sp-bar-overlay";
                            overlay.style.cssText = "position:fixed;left:0;right:0;z-index:550;background:#121212;pointer-events:none;";
                            document.body.appendChild(overlay);
                        }}
                        // ヘッダー〜ボタンバー下端まで塞ぐ
                        overlay.style.top = "0";
                        overlay.style.height = fixedTopVal + "px";
                        overlay.style.display = "block";
                    }} else {{
                        tb.style.position = "";
                        tb.style.top = "";
                        tb.style.left = "";
                        tb.style.width = "";
                        tb.style.background = "";
                        if (ab) {{
                            ab.style.position = "";
                            ab.style.top = "";
                            ab.style.left = "";
                            ab.style.width = "";
                            ab.style.background = "";
                        }}
                        if (cd) cd.style.marginTop = "20px";
                        var overlay2 = document.getElementById("sp-bar-overlay");
                        if (overlay2) overlay2.style.display = "none";
                    }}
                }});
            }});
        </script>"""
        
        self.message_user(request, mark_safe(COMMON_STYLE + custom_css + accordion_html + pagination_html))
            
        return super().changelist_view(request, extra_context)

    class Media: js = ('catalog/js/pos_system.js',)

    @admin.action(description="✅ 選択した商品を保管庫へ移動")
    def move_to_archive(self, request, queryset): queryset.update(is_archived=True)
    @admin.action(description="⏪ 選択した商品を商品一覧に戻す")
    def restore_from_archive(self, request, queryset): queryset.update(is_archived=False)

@admin.register(Show_ProductList_A4)
class A4PosterAdmin(BaseProductAdmin):
    def get_queryset(self, request):
        import datetime
        from django.db.models import ExpressionWrapper, F, fields
        qs = super().get_queryset(request).filter(category='A4', is_archived=False)
        xsort = getattr(request, '_xsort_val', '')
        if xsort in ['asc', 'desc']:
            qs = qs.annotate(deadline=ExpressionWrapper(
                F('created_at') + F('duration_days') * datetime.timedelta(days=1),
                output_field=fields.DateTimeField()
            ))
            return qs.order_by('deadline' if xsort == 'asc' else '-deadline')
        return qs
@admin.register(Z_Archive_A4)
class A4ArchiveAdmin(BaseProductAdmin):
    def get_queryset(self, request): return super().get_queryset(request).filter(category='A4', is_archived=True)
    def has_view_permission(self, request, obj=None): return request.user.is_superuser or request.user.username == 'kawaii-girlgallery'
@admin.register(Show_ProductList_TCG)
class TCGCardAdmin(BaseProductAdmin):
    def get_queryset(self, request):
        import datetime
        from django.db.models import ExpressionWrapper, F, fields
        qs = super().get_queryset(request).filter(category='TCG', is_archived=False)
        xsort = getattr(request, '_xsort_val', '')
        if xsort in ['asc', 'desc']:
            qs = qs.annotate(deadline=ExpressionWrapper(
                F('created_at') + F('duration_days') * datetime.timedelta(days=1),
                output_field=fields.DateTimeField()
            ))
            return qs.order_by('deadline' if xsort == 'asc' else '-deadline')
        return qs
@admin.register(Z_Archive_TCG)
class TCGArchiveAdmin(BaseProductAdmin):
    def get_queryset(self, request): return super().get_queryset(request).filter(category='TCG', is_archived=True)
    def has_view_permission(self, request, obj=None): return request.user.is_superuser or request.user.username == 'kawaii-girlgallery'

def character_pedia_view(request):
    mode = request.GET.get('mode', 'char')
    page_title = "原作作品一覧" if mode == 'work' else "キャラクター一覧"
    app_config = apps.get_app_config('catalog')
    app_config.verbose_name = "一覧表"
    context = {
        **admin.site.each_context(request),
        'title': page_title,
        'cl_class': 'pedia-mode', 
    }
    qs = Product.objects.filter(is_archived=False)
    data = {}
    for p in qs:
        parts = re.split(r'[ _　]', p.name)
        if mode == 'work':
            work_parts = []
            if len(parts) > 1:
                for part in parts[1:]:
                    if "同人" in part: break
                    if re.match(r'^G\d+$', part, re.IGNORECASE): break
                    work_parts.append(part)
            key = " ".join(work_parts).strip() if work_parts else "単体作品"
        else:
            char_name = parts[0] if parts else "不明"
            char_name = re.sub(r'【.*?】', '', char_name).strip()
            if not char_name and len(parts) > 1:
                char_name = re.sub(r'【.*?】', '', parts[1]).strip()
            key = char_name if char_name else "不明"
            
        if key not in data: 
            data[key] = {'A4': 0, 'TCG': 0, 'total': 0, 'images': [], 'a4_url': f"/admin/catalog/show_productlist_a4/?q={key}", 'tcg_url': f"/admin/catalog/show_productlist_tcg/?q={key}"}
        if 'A4' in str(p.category).upper(): data[key]['A4'] += 1
        elif 'TCG' in str(p.category).upper(): data[key]['TCG'] += 1
        data[key]['total'] += 1
        if p.image: data[key]['images'].append(p.image.url)
    char_list = [(k, v, random.choice(v['images']) if v['images'] else None) for k, v in data.items()]
    context['char_list'] = sorted(char_list, key=lambda x: x[1]['total'], reverse=True)
    messages.info(request, mark_safe(COMMON_STYLE))
    return render(request, 'admin/catalog/character_pedia.html', context)

def sales_dashboard_view(request):
    if request.method == 'POST' and request.POST.get('reset_sales') == 'true':
        if request.user.is_superuser or request.user.username == 'kawaii-girlgallery':
            Sale.objects.all().delete()
            messages.success(request, "売上データをすべてリセットしました。")
            return redirect(request.path)

    s_dt, e_dt, period = get_date_range(request)
    sales_qs = Sale.objects.filter(sold_at__range=(s_dt, e_dt))

    def calc_stats(qs):
        total_customers = qs.values('user').distinct().count()
        total_items = qs.count()
        return {
            'total_revenue': qs.aggregate(Sum('price'))['price__sum'] or 0,
            'total_items': total_items,
            'total_customers': total_customers,
            'avg_items': round(total_items / total_customers, 1) if total_customers > 0 else 0
        }

    stats_all = calc_stats(sales_qs)
    stats_a4 = calc_stats(sales_qs.filter(category='A4'))
    stats_tcg = calc_stats(sales_qs.filter(category='TCG'))

    return render(request, 'admin/catalog/sales_dashboard.html', {
        **admin.site.each_context(request),
        'stats': stats_all,
        'stats_a4': stats_a4,
        'stats_tcg': stats_tcg,
        'period_title': period,
        'start_date': s_dt.strftime('%Y-%m-%d'),
        'end_date': e_dt.strftime('%Y-%m-%d'),
        'is_admin': request.user.is_superuser or request.user.username == 'kawaii-girlgallery',
        'cl_class': 'admin-custom-mode'
    })

def analysis_sheet_view(request):
    if request.method == 'POST' and request.POST.get('reset_sales') == 'true':
        if request.user.is_superuser or request.user.username == 'kawaii-girlgallery':
            Sale.objects.all().delete()
            messages.success(request, "売上データをすべてリセットしました。")
            return redirect(request.path)

    s_dt, e_dt, period = get_date_range(request)
    sales_all = Sale.objects.filter(sold_at__range=(s_dt, e_dt))

    def calc_analysis(sales):
        char_s, work_s = {}, {}
        weekday_list = [{"name": n, "revenue": 0, "count": 0} for n in ["月", "火", "水", "木", "金", "土", "日"]]
        for s in sales:
            parts = re.split(r'[ _　]', s.product_name)
            c = re.sub(r'【.*?】', '', parts[0] if parts else '').strip()
            if not c and len(parts) > 1:
                c = re.sub(r'【.*?】', '', parts[1]).strip()
            c = c or "不明"
            work_parts = []
            if len(parts) > 1:
                for part in parts[1:]:
                    if "同人" in part: break
                    if re.match(r'^G\d+$', part, re.IGNORECASE): break
                    work_parts.append(part)
            w = " ".join(work_parts).strip() if work_parts else "単体作品"
            if c not in char_s: char_s[c] = {'count': 0, 'revenue': 0}
            char_s[c]['count'] += 1; char_s[c]['revenue'] += s.price
            if w not in work_s: work_s[w] = {'count': 0, 'revenue': 0}
            work_s[w]['count'] += 1; work_s[w]['revenue'] += s.price
            idx = timezone.localtime(s.sold_at).weekday()
            weekday_list[idx]['revenue'] += s.price; weekday_list[idx]['count'] += 1
        return {
            'char_sales': sorted(char_s.items(), key=lambda x: x[1]['revenue'], reverse=True),
            'work_sales': sorted(work_s.items(), key=lambda x: x[1]['revenue'], reverse=True),
            'weekday_sales': weekday_list,
        }

    data_all = calc_analysis(sales_all)
    data_a4 = calc_analysis(sales_all.filter(category='A4'))
    data_tcg = calc_analysis(sales_all.filter(category='TCG'))

    return render(request, 'admin/catalog/analysis_sheet.html', {
        **admin.site.each_context(request),
        'char_sales': data_all['char_sales'],
        'work_sales': data_all['work_sales'],
        'weekday_sales': data_all['weekday_sales'],
        'char_sales_a4': data_a4['char_sales'],
        'work_sales_a4': data_a4['work_sales'],
        'char_sales_tcg': data_tcg['char_sales'],
        'work_sales_tcg': data_tcg['work_sales'],
        'weekday_sales_a4': data_a4['weekday_sales'],
        'weekday_sales_tcg': data_tcg['weekday_sales'],
        'period_title': period,
        'start_date': s_dt.strftime('%Y-%m-%d'),
        'end_date': e_dt.strftime('%Y-%m-%d'),
        'is_admin': request.user.is_superuser or request.user.username == 'kawaii-girlgallery',
        'cl_class': 'admin-custom-mode'
    })

def generate_order_number():
    """注文番号を生成する KG-YYYYMMDD-XXX"""
    from django.utils import timezone as tz
    today = tz.localtime(tz.now()).strftime('%Y%m%d')
    count = Sale.objects.filter(sold_at__date=tz.localtime(tz.now()).date()).values('order_number').distinct().count() + 1
    return f"KG-{today}-{count:03d}"

def order_receipt_view(request, order_number):
    """お迎え証明書ページ"""
    sales = Sale.objects.filter(order_number=order_number)
    if not sales.exists():
        from django.http import Http404
        raise Http404
    total = sum(s.price for s in sales)
    buyer_name = sales.first().buyer_name
    sold_at = sales.first().sold_at
    return render(request, 'admin/catalog/order_receipt.html', {
        'order_number': order_number,
        'sales': sales,
        'total': total,
        'buyer_name': buyer_name,
        'sold_at': sold_at,
    })

def order_management_view(request):
    from django.utils import timezone as tz
    from django.db.models import Q
    import calendar

    if request.method == 'POST' and request.POST.get('reset_all') == 'true':
        if request.user.is_superuser or request.user.username == 'kawaii-girlgallery':
            Sale.objects.all().delete()
            OrderManagement.objects.all().delete()
            messages.success(request, "売上・注文データをすべてリセットしました。")
            return redirect(request.path)

    now = tz.localtime(tz.now())
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    search = request.GET.get('q', '')
    status = request.GET.get('status', 'all')
    page = int(request.GET.get('page', 1))
    per_page = 20

    qs = OrderManagement.objects.filter(sold_at__year=year, sold_at__month=month)
    if search:
        qs = qs.filter(buyer_name__icontains=search)
    if status == 'done':
        qs = qs.filter(check_listed=True, check_sold=True, check_shipped=True)
    elif status == 'undone':
        qs = qs.exclude(check_listed=True, check_sold=True, check_shipped=True)

    total_count = qs.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    orders = qs[(page-1)*per_page:page*per_page]

    first = OrderManagement.objects.order_by('sold_at').first()
    month_list = []
    if first:
        cur = first.sold_at.replace(day=1)
        end = now.replace(day=1)
        while cur <= end:
            month_list.append({'year': cur.year, 'month': cur.month, 'label': f"{cur.year}年{cur.month}月"})
            if cur.month == 12:
                cur = cur.replace(year=cur.year+1, month=1)
            else:
                cur = cur.replace(month=cur.month+1)
        month_list.reverse()

    return render(request, 'admin/catalog/order_management.html', {
        **admin.site.each_context(request),
        'orders': orders,
        'total_count': total_count,
        'total_pages': total_pages,
        'current_page': page,
        'year': year,
        'month': month,
        'search': search,
        'status': status,
        'month_list': month_list,
        'current_label': f"{year}年{month}月",
        'is_admin': request.user.is_superuser or request.user.username == 'kawaii-girlgallery',
        'cl_class': 'admin-custom-mode',
    })

def order_management_update_view(request):
    """注文管理のAjax更新エンドポイント"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)
    data = json.loads(request.body)
    order_number = data.get('order_number')
    try:
        order = OrderManagement.objects.get(order_number=order_number)
        if 'yahoo_url' in data: order.yahoo_url = data['yahoo_url']
        if 'check_listed' in data: order.check_listed = data['check_listed']
        if 'check_sold' in data: order.check_sold = data['check_sold']
        if 'check_shipped' in data: order.check_shipped = data['check_shipped']
        order.save()
        return JsonResponse({'status': 'success', 'is_completed': order.is_completed})
    except OrderManagement.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '注文が見つかりません'}, status=404)

def send_line_notification(message):
    """LINE Messaging APIで管理者に通知を送る"""
    try:
        import requests as req
        token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
        user_id = os.environ.get('LINE_USER_ID')
        if not token or not user_id:
            print("LINE credentials not set")
            return
        req.post(
            'https://api.line.me/v2/bot/message/push',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'to': user_id, 'messages': [{'type': 'text', 'text': message}]}
        )
    except Exception as e:
        print(f"LINE notification error: {e}")

def record_sale_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        items = data.get('items', [])
        buyer_name = data.get('buyer_name', '')
        order_number = generate_order_number()
        for i in items:
            Sale.objects.create(
                product_name=i['name'],
                price=i['price'],
                category=i.get('category', ''),
                buyer_name=buyer_name,
                order_number=order_number,
                user=request.user if request.user.is_authenticated else None
            )
        total = sum(i['price'] for i in items)
        item_lines = '\n'.join([f"・{i['name']} ¥{i['price']}" for i in items])
        message = f"💖 お迎え完了！\n購入者：{buyer_name}\n{item_lines}\n合計: ¥{total:,}\n注文番号：{order_number}"
        send_line_notification(message)
        from django.utils import timezone as tz
        product_names = '\n'.join([i['name'] for i in items])
        OrderManagement.objects.create(
            order_number=order_number,
            buyer_name=buyer_name,
            total_price=total,
            product_names=product_names,
            sold_at=tz.now(),
        )
        return JsonResponse({'status': 'success', 'order_number': order_number, 'buyer_name': buyer_name})
    return JsonResponse({'status': 'error'}, status=405)

def get_custom_urls(self):
    return [
        path('sales-dashboard/', self.admin_view(sales_dashboard_view)),
        path('analysis-sheet/', self.admin_view(analysis_sheet_view)),
        path('character-pedia/', self.admin_view(character_pedia_view)),
        path('record-sale/', self.admin_view(record_sale_view)),
        path('order-receipt/<str:order_number>/', order_receipt_view, name='order_receipt'),
        path('order-management/', self.admin_view(order_management_view)),
        path('order-management/update/', self.admin_view(order_management_update_view)),
    ] + self.get_urls_original()

if not hasattr(admin.AdminSite, 'get_urls_original'):
    admin.AdminSite.get_urls_original = admin.AdminSite.get_urls
    admin.AdminSite.get_urls = get_custom_urls

def get_date_range(request):
    now = timezone.now()
    s_str, e_str = request.GET.get('start_date'), request.GET.get('end_date')
    s_dt = timezone.make_aware(datetime.strptime(s_str, '%Y-%m-%d')) if s_str else now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    e_dt = timezone.make_aware(datetime.strptime(e_str, '%Y-%m-%d')).replace(hour=23, minute=59, second=59) if e_str else now.replace(hour=23, minute=59, second=59, microsecond=999999)
    return s_dt, e_dt, f"{s_dt.year}年{s_dt.month}月" if not s_str else f"{s_str}〜{e_str}"

def get_app_list(self, request, app_label=None):
    app_dict = self._build_app_dict(request, app_label)
    catalog = app_dict.get('catalog')
    is_admin = request.user.is_superuser or request.user.username == 'kawaii-girlgallery'
    if not catalog: return list(app_dict.values()) if is_admin else []
    m_list = catalog['models']
    def get_m(name): return next((m for m in m_list if m['object_name'] == name), None)
    pedia_models = [{'name': '原作一覧', 'admin_url': '/admin/character-pedia/?mode=work'}, {'name': 'キャラクター一覧', 'admin_url': '/admin/character-pedia/?mode=char'}]
    a4_models = [get_m('Show_ProductList_A4')]
    if is_admin: a4_models.append(get_m('Z_Archive_A4'))
    tcg_models = [get_m('Show_ProductList_TCG')]
    if is_admin: tcg_models.append(get_m('Z_Archive_TCG'))
    final_list = [{'name': '一覧表', 'app_label': 'catalog_pedia', 'models': pedia_models, 'has_module_permission': True}, {'name': 'A4サイズポスター', 'app_label': 'catalog_a4', 'models': a4_models, 'has_module_permission': True}, {'name': 'トレーディングカード', 'app_label': 'catalog_tcg', 'models': tcg_models, 'has_module_permission': True}]
    if is_admin:
        lib_models = [{'name': 'ユーザー認証', 'admin_url': '/admin/auth/user/'}, {'name': '売上ダッシュボード', 'admin_url': '/admin/sales-dashboard/'}, {'name': 'インサイト分析', 'admin_url': '/admin/analysis-sheet/'}, {'name': '注文管理', 'admin_url': '/admin/order-management/'}]
        if get_m('Sale'): lib_models.append(get_m('Sale'))
        final_list.append({'name': '図鑑管理', 'app_label': 'catalog_admin_custom', 'models': lib_models, 'has_module_permission': True})
    return final_list

admin.AdminSite.get_app_list = get_app_list

def index_view_custom(self, request, extra_context=None):
    base_products = list(Product.objects.only('image').filter(is_archived=False).order_by('?')[:50])
    full_list = base_products * 5 
    random.shuffle(full_list)
    tiles_html = '<div class="home-tile-bg">'
    for p in full_list:
        if p.image: tiles_html += f'<img src="{p.image.url}">'
    tiles_html += '</div>'
    messages.info(request, mark_safe(COMMON_STYLE + tiles_html))
    return self.index_original(request, extra_context)

if not hasattr(admin.AdminSite, 'index_original'):
    admin.AdminSite.index_original = admin.AdminSite.index
    admin.AdminSite.index = index_view_custom

admin.site.site_header = mark_safe('💕 kawaii女の子図鑑')
admin.site.index_title = '図鑑管理ダッシュボード'

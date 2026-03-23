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
from .models import Product, Show_ProductList_A4, Z_Archive_A4, Show_ProductList_TCG, Z_Archive_TCG, Sale

# ✨ 共通CSS定義
COMMON_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rounded+Mplus+1c:wght@700;900&display=swap');
    body, #header, #content, #nav-sidebar, h1, h2, h3, .module caption { font-family: 'Rounded Mplus 1c', sans-serif !important; }
    
    .messagelist { background: none !important; border: none !important; box-shadow: none !important; padding: 0 !important; margin: 0 !important; }
    .messagelist li { background: none !important; border: none !important; padding: 0 !important; color: transparent !important; margin-bottom: 0 !important; }
    .messagelist li > div { color: initial !important; }

    #header { background: #1a1c23 !important; padding: 15px 25px !important; border-bottom: 4px solid transparent !important; border-image: linear-gradient(to right, #ff4d94, #2684ff, #f0ad4e) 1 !important; position: sticky !important; top: 0 !important; z-index: 1000 !important; }
    #branding h1 { font-size: 28px !important; font-weight: 900 !important; display: flex !important; align-items: center !important; gap: 12px !important; background: linear-gradient(to right, #ff69b4, #2684ff, #f0ad4e) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; }
    #branding h1::before { content: '💕'; -webkit-text-fill-color: initial !important; font-size: 26px; }
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
    .breadcrumbs { position: sticky !important; top: 75px !important; z-index: 999 !important; background: #1a1c23 !important; }
    nav { height: auto !important; overflow: visible !important; }
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
    images = MultipleFileField(label='画像ファイル選択')

class BaseProductAdmin(admin.ModelAdmin):
    list_display = ('display_name_jp', 'display_image_jp', 'display_price_jp', 'display_timer_jp')
    list_display_links = None 
    search_fields = ('name',)
    actions = ['move_to_archive', 'restore_from_archive']

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.username == 'kawaii-girlgallery'

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            actions['delete_selected'] = (actions['delete_selected'][0], actions['delete_selected'][1], "✅ 選択した商品を削除")
        if not self.has_change_permission(request): return {} 
        is_archive_page = 'Archive' in self.__class__.__name__
        if is_archive_page:
            if 'move_to_archive' in actions: del actions['move_to_archive']
        else:
            if 'restore_from_archive' in actions: del actions['restore_from_archive']
        return actions

    def get_urls(self):
        return [path('bulk-upload/', self.admin_site.admin_view(self.bulk_upload), name='bulk_upload')] + super().get_urls()

    def bulk_upload(self, request):
        if not self.has_change_permission(request): return redirect('..')
        if request.method == 'POST':
            form = BulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                cat, pr = form.cleaned_data['category'], form.cleaned_data['price']
                for f in request.FILES.getlist('images'):
                    Product.objects.create(name=os.path.splitext(f.name)[0], category=cat, price=pr, image=f)
                return redirect('..')
        return render(request, 'admin/catalog/bulk_upload.html', {**self.admin_site.each_context(request), 'form': BulkUploadForm(initial={'category': 'A4' if 'a4' in request.path else 'TCG'}), 'title': '一括アップロード'})

    def display_name_jp(self, obj): return format_html('<div class="cell-center" style="font-weight: 800;">{}</div>', obj.name)
    display_name_jp.short_description = '商品名'
    def display_image_jp(self, obj):
        if not obj.image: return "なし"
        return format_html('<div class="cell-center"><img src="{}" style="max-height:150px;max-width:150px;border:3px solid #444; border-radius:10px;"></div>', obj.image.url)
    display_image_jp.short_description = '画像'
    def display_price_jp(self, obj): return format_html('<div class="cell-center" style="font-weight: 900; color: #00ffcc;">¥{}</div>', obj.price)
    display_price_jp.short_description = '価格'
    def display_timer_jp(self, obj): return format_html('<div class="cell-center"><div class="timer-display" data-date="{}" style="font-weight: 800;">⏳ ...</div></div>', obj.created_at.isoformat())
    display_timer_jp.short_description = '掲載期限'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        is_archive = 'Archive' in self.__class__.__name__
        app_config = apps.get_app_config('catalog')
        if "a4" in self.__class__.__name__.lower():
            cat_filter = 'A4'
            app_config.verbose_name = "A4サイズポスター"
        else:
            cat_filter = 'TCG'
            app_config.verbose_name = "トレーディングカード"
        extra_context['title'] = "保管庫" if is_archive else "商品一覧"
        
        cl = self.get_changelist_instance(request)
        from django.contrib.admin.templatetags.admin_list import pagination as pagination_tag
        pag_context = pagination_tag(cl)
        pagination_html = format_html('<div class="top-paginator">{}</div>', render_to_string('admin/pagination.html', pag_context))
        
        char_counts, work_counts = {}, {}
        full_qs = Product.objects.filter(category=cat_filter, is_archived=is_archive)
        
        for p in full_qs:
            parts = re.split(r'[ _　]', p.name)
            char_name = parts[0] if parts else "不明"
            char_counts[char_name] = char_counts.get(char_name, 0) + 1
            
            if len(parts) > 1:
                work_parts = []
                for part in parts[1:]:
                    if "同人" in part: break
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

        is_admin_flag = 'true' if self.has_change_permission(request) else 'false'

        # アコーディオンパネルHTML + CSS + JS
        accordion_html = mark_safe(f'''
<style>
    /* アコーディオンタブ */
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

    /* パネル本体 */
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
    /* スクロールバー */
    .qs-panel-body::-webkit-scrollbar {{ width: 6px; }}
    .qs-panel-body::-webkit-scrollbar-track {{ background: #1a1a1a; }}
    .qs-panel-body::-webkit-scrollbar-thumb {{ background: #444; border-radius: 3px; }}

    /* 元のクイック検索パネルを非表示 */
    .messagelist {{ display: none !important; }}
    .top-paginator {{ display: none !important; }}
</style>

<!-- キャラクタータブ -->
<div class="qs-tab-wrap">
    <div class="qs-tab qs-tab-char" onclick="togglePanel('char-panel')">👤 キャラクター検索</div>
    <div class="qs-tab qs-tab-work" onclick="togglePanel('work-panel')">🎬 原作作品検索</div>
</div>

<!-- キャラクター検索パネル -->
<div id="char-panel" class="qs-panel" style="border-left: 3px solid #ff69b4;">
    <div class="qs-panel-header">
        <div class="qs-panel-title" style="color: #ff69b4;">👤 キャラクター検索 {back_btn_html}</div>
        <div class="qs-panel-close" onclick="closePanel('char-panel')">✕</div>
    </div>
    <div class="qs-panel-body">{char_btns}</div>
</div>

<!-- 原作作品検索パネル -->
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
            #result_list thead th, #result_list tbody td {{ text-align: center !important; vertical-align: middle !important; padding: 12px 5px !important; font-weight: 700; }}
            #result_list thead {{ position: sticky !important; top: 101px !important; z-index: 98 !important; }}
            #result_list thead th {{ background: #1a1a1a !important; }}
            .cell-center {{ display: flex; align-items: center; justify-content: center; height: 170px; width: 100%; }}

            /* 商品一覧タイトルを非表示 */
            #content h1 {{ display: none !important; }}

            /* 元の検索・ツールボックス・操作行・ページネーターを非表示 */
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

            /* 検索窓行 */
            .smart-top-bar {{
                position: sticky !important;
                top: 0 !important;
                z-index: 100 !important;
                display: flex;
                align-items: center;
                gap: 10px;
                background: #1a1a1a;
                padding: 10px 15px;
                border-radius: 10px;
                margin-bottom: 4px;
                flex-wrap: nowrap;
                box-sizing: border-box;
            }}
            .smart-search-form {{ display: flex; align-items: center; gap: 6px; flex-shrink: 0; }}
            .smart-search-form input[type=text] {{
                background: #2a2a2a; border: 1px solid #555; color: #fff;
                border-radius: 8px; padding: 5px 12px; font-size: 13px; font-weight: 700; width: 140px;
            }}
            .smart-search-form input[type=submit] {{
                background: #333; border: 1px solid #555; color: #fff;
                border-radius: 8px; padding: 5px 12px; font-size: 12px; font-weight: 900; cursor: pointer;
            }}
            .smart-paginator {{ display: flex; align-items: center; gap: 4px; flex-shrink: 0; }}
            .smart-paginator a, .smart-paginator span.this-page {{
                display: inline-flex !important; align-items: center; justify-content: center;
                min-width: 28px; height: 28px; padding: 0 6px;
                background: #2a2a2a; border: 1px solid #444; border-radius: 6px;
                color: #00ffcc !important; font-weight: 900; font-size: 13px; text-decoration: none;
            }}
            .smart-paginator span.this-page {{
                background: #007bff; border-color: #007bff; color: #fff !important;
            }}
            .smart-paginator .total-count {{
                color: #aaa; font-size: 12px; font-weight: 700; white-space: nowrap; margin-left: 4px;
            }}
            .smart-top-bar-spacer {{ flex: 1; }}
            .smart-btn-group {{ display: flex; align-items: center; gap: 8px; flex-shrink: 0; }}

            /* 操作行 */
            .smart-action-bar {{
                position: sticky !important;
                top: 53px !important;
                z-index: 99 !important;
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

            #pos-modal {{ background-color: rgba(0, 0, 0, 0.98) !important; display: none; position: fixed !important; z-index: 20000 !important; top: 0; left: 0; width: 100vw; height: 100vh; }}
            .modal-nav {{ position: fixed !important; top: 50% !important; transform: translateY(-50%) !important; font-size: 80px !important; color: rgba(255,255,255,0.4) !important; z-index: 20020 !important; cursor: pointer; padding: 20px; }}
            .nav-prev {{ left: 2vw !important; }} .nav-next {{ right: 2vw !important; }}
            .modal-center-container {{ display: flex !important; justify-content: center !important; align-items: center !important; height: 100vh !important; width: 100vw !important; }}
            .modal-main-unit {{ display: flex !important; flex-direction: column !important; align-items: center !important; }}
            .modal-content {{ max-height: 70vh !important; max-width: 80vw !important; border: 3px solid #fff !important; border-radius: 0 !important; display: block !important; }}
            #modal-add-btn {{ position: fixed !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 40px !important; background: rgba(40, 167, 69, 0.9) !important; color: white !important; font-size: 15px !important; font-weight: 900 !important; border: none !important; border-bottom: 2px solid #fff !important; z-index: 21000 !important; display: flex !important; align-items: center !important; justify-content: center !important; cursor: pointer !important; }}
            .close-btn {{ position: fixed !important; top: 50px !important; right: 30px !important; color: #fff !important; font-size: 50px !important; z-index: 21100 !important; cursor: pointer; }}
        </style>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                // ✨ アコーディオンパネルとタブをbodyに移動（messagelistから脱出）
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

                // 検索窓行
                var topBar = document.createElement('div');
                topBar.className = 'smart-top-bar';

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
                    var pagDiv = document.createElement('div');
                    pagDiv.className = 'smart-paginator';
                    var lis = origPaginator.querySelectorAll('li');
                    if (lis.length > 0) {{
                        lis.forEach(function(li) {{
                            var a = li.querySelector('a');
                            var s = li.querySelector('span.this-page');
                            if (a) {{
                                var newA = document.createElement('a');
                                newA.href = a.href;
                                newA.textContent = a.textContent.trim();
                                pagDiv.appendChild(newA);
                            }} else if (s) {{
                                var newS = document.createElement('span');
                                newS.className = 'this-page';
                                newS.textContent = s.textContent.trim();
                                pagDiv.appendChild(newS);
                            }}
                        }});
                    }} else {{
                        origPaginator.querySelectorAll('a').forEach(function(a) {{
                            var newA = document.createElement('a');
                            newA.href = a.href;
                            newA.textContent = a.textContent.trim();
                            pagDiv.appendChild(newA);
                        }});
                    }}
                    var totalText = origPaginator.textContent.match(/\d+\s*商品一覧/);
                    if (totalText) {{
                        var countSpan = document.createElement('span');
                        countSpan.className = 'total-count';
                        countSpan.textContent = totalText[0];
                        pagDiv.appendChild(countSpan);
                    }}
                    topBar.appendChild(pagDiv);
                }}

                var spacer = document.createElement('div');
                spacer.className = 'smart-top-bar-spacer';
                topBar.appendChild(spacer);

                var btnGroup = document.createElement('div');
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

                if ({is_admin_flag} === true) {{
                    var btnUpload = document.createElement('a');
                    btnUpload.href = 'bulk-upload/';
                    btnUpload.innerHTML = '📂 一括アップロード ＋';
                    btnUpload.style.cssText = 'background:#f0ad4e; color:#fff; padding:6px 16px; border-radius:20px; font-weight:900; text-decoration:none; font-size:13px;';
                    btnGroup.appendChild(btnUpload);
                }}
                topBar.appendChild(btnGroup);

                // 操作行
                var actionBar = document.createElement('div');
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
                        if (sel) sel.value = actionBar.querySelector('select').value;
                        var origRun = origActions.querySelector('input[type=submit]');
                        if (origRun) origRun.click();
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

                changelist.parentNode.insertBefore(actionBar, changelist);
                // ✨ タブとパネルをbodyに移動（fixed positionを効かせるため）
                var tabWrap = document.querySelector(".qs-tab-wrap");
                var charPanel = document.querySelector("#char-panel");
                var workPanel = document.querySelector("#work-panel");
                if (tabWrap) document.body.appendChild(tabWrap);
                if (charPanel) document.body.appendChild(charPanel);
                if (workPanel) document.body.appendChild(workPanel);
                changelist.parentNode.insertBefore(topBar, actionBar);
            }});
        </script>"""
        
        storage = messages.get_messages(request)
        is_already_sent = any("キャラクタークイック検索" in str(m) for m in storage)
        storage.used = False 
        
        if not is_already_sent:
            self.message_user(request, mark_safe(COMMON_STYLE + custom_css + accordion_html + pagination_html))
            
        return super().changelist_view(request, extra_context)

    class Media: js = ('catalog/js/pos_system.js',)

    @admin.action(description="✅ 選択した商品を保管庫へ移動")
    def move_to_archive(self, request, queryset): queryset.update(is_archived=True)
    @admin.action(description="⏪ 選択した商品を商品一覧に戻す")
    def restore_from_archive(self, request, queryset): queryset.update(is_archived=False)

@admin.register(Show_ProductList_A4)
class A4PosterAdmin(BaseProductAdmin):
    def get_queryset(self, request): return super().get_queryset(request).filter(category='A4', is_archived=False)
@admin.register(Z_Archive_A4)
class A4ArchiveAdmin(BaseProductAdmin):
    def get_queryset(self, request): return super().get_queryset(request).filter(category='A4', is_archived=True)
@admin.register(Show_ProductList_TCG)
class TCGCardAdmin(BaseProductAdmin):
    def get_queryset(self, request): return super().get_queryset(request).filter(category='TCG', is_archived=False)
@admin.register(Z_Archive_TCG)
class TCGArchiveAdmin(BaseProductAdmin):
    def get_queryset(self, request): return super().get_queryset(request).filter(category='TCG', is_archived=True)

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
                    work_parts.append(part)
            key = " ".join(work_parts).strip() if work_parts else "単体作品"
        else:
            key = parts[0] if parts else "不明"
            
        if key not in data: 
            data[key] = {'A4': 0, 'TCG': 0, 'total': 0, 'images': [], 'a4_url': f"/admin/catalog/show_productlist_a4/?q={key}", 'tcg_url': f"/admin/catalog/show_productlist_tcg/?q={key}"}
        if 'A4' in str(p.category).upper(): data[key]['A4'] += 1
        elif 'TCG' in str(p.category).upper(): data[key]['TCG'] += 1
        data[key]['total'] += 1
        if p.image: data[key]['images'].append(p.image.url)
    char_list = [(k, v, random.choice(v['images']) if v['images'] else None) for k, v in data.items()]
    context['char_list'] = sorted(char_list, key=lambda x: x[1]['total'], reverse=True)
    return render(request, 'admin/catalog/character_pedia.html', context)

def sales_dashboard_view(request):
    if request.method == 'POST' and request.POST.get('reset_sales') == 'true':
        if request.user.is_superuser or request.user.username == 'kawaii-girlgallery':
            Sale.objects.all().delete()
            messages.success(request, "売上データをすべてリセットしました。")
            return redirect(request.path)

    s_dt, e_dt, period = get_date_range(request)
    sales_qs = Sale.objects.filter(sold_at__range=(s_dt, e_dt))
    total_customers = sales_qs.values('user').distinct().count()
    stats = {'total_revenue': sales_qs.aggregate(Sum('price'))['price__sum'] or 0, 'total_items': sales_qs.count(), 'total_customers': total_customers, 'avg_items': round(sales_qs.count() / total_customers, 1) if total_customers > 0 else 0}
    
    return render(request, 'admin/catalog/sales_dashboard.html', {
        **admin.site.each_context(request), 
        'stats': stats, 'period_title': period, 'start_date': s_dt.strftime('%Y-%m-%d'), 'end_date': e_dt.strftime('%Y-%m-%d'),
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
    sales = Sale.objects.filter(sold_at__range=(s_dt, e_dt))
    char_s, work_s = {}, {}
    weekday_list = [{"name": n, "revenue": 0, "count": 0} for n in ["月", "火", "水", "木", "金", "土", "日"]]
    for s in sales:
        parts = re.split(r'[ _　]', s.product_name)
        c = parts[0] if parts else "不明"
        
        work_parts = []
        if len(parts) > 1:
            for part in parts[1:]:
                if "同人" in part: break
                work_parts.append(part)
        w = " ".join(work_parts).strip() if work_parts else "単体作品"

        if c not in char_s: char_s[c] = {'count': 0, 'revenue': 0}
        char_s[c]['count'] += 1; char_s[c]['revenue'] += s.price
        if w not in work_s: work_s[w] = {'count': 0, 'revenue': 0}
        work_s[w]['count'] += 1; work_s[w]['revenue'] += s.price
        idx = timezone.localtime(s.sold_at).weekday()
        weekday_list[idx]['revenue'] += s.price; weekday_list[idx]['count'] += 1
    
    return render(request, 'admin/catalog/analysis_sheet.html', {
        **admin.site.each_context(request), 
        'char_sales': sorted(char_s.items(), key=lambda x: x[1]['revenue'], reverse=True), 
        'work_sales': sorted(work_s.items(), key=lambda x: x[1]['revenue'], reverse=True), 
        'weekday_sales': weekday_list, 'period_title': period, 'start_date': s_dt.strftime('%Y-%m-%d'), 'end_date': e_dt.strftime('%Y-%m-%d'),
        'is_admin': request.user.is_superuser or request.user.username == 'kawaii-girlgallery',
        'cl_class': 'admin-custom-mode' 
    })

def record_sale_view(request):
    if request.method == 'POST':
        items = json.loads(request.body).get('items', [])
        for i in items: Sale.objects.create(product_name=i['name'], price=i['price'], user=request.user if request.user.is_authenticated else None)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=405)

def get_custom_urls(self):
    return [path('sales-dashboard/', self.admin_view(sales_dashboard_view)), path('analysis-sheet/', self.admin_view(analysis_sheet_view)), path('character-pedia/', self.admin_view(character_pedia_view)), path('record-sale/', self.admin_view(record_sale_view))] + self.get_urls_original()

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
        lib_models = [{'name': 'ユーザー認証', 'admin_url': '/admin/auth/user/'}, {'name': '売上ダッシュボード', 'admin_url': '/admin/sales-dashboard/'}, {'name': 'インサイト分析', 'admin_url': '/admin/analysis-sheet/'}]
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

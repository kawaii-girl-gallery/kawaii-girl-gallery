function updateTimers() {
    const now = new Date();
    document.querySelectorAll('.timer-display').forEach(elem => {
        const dataDate = elem.getAttribute('data-date');
        if (!dataDate) return;
        const deadline = new Date(dataDate);
        deadline.setDate(deadline.getDate() + 6);
        deadline.setHours(23, 59, 59, 999);
        const diff = deadline - now;
        if (diff <= 0) {
            elem.innerText = "【掲載終了】";
            elem.style.color = "#ff4444";
        } else {
            const d = Math.floor(diff / 86400000);
            const h = String(Math.floor((diff / 3600000) % 24)).padStart(2, '0');
            const m = String(Math.floor((diff / 60000) % 60)).padStart(2, '0');
            const s = String(Math.floor((diff / 1000) % 60)).padStart(2, '0');
            elem.innerText = `⏳ 残り ${d}日 ${h}:${m}:${s}`;
        }
    });
}
setInterval(updateTimers, 1000);

let currentImages = []; 
let currentIndex = 0;

function openCarousel(imgUrl, name, price) {
    let modal = document.getElementById('pos-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'pos-modal';
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <span class="close-btn" onclick="closeModal()">&times;</span>
        <button id="modal-add-btn" onclick="addCurrentToCart(event)">🛒 この商品をカートへ追加</button>
        <div class="modal-nav nav-prev" onclick="prevImg(event)">&#10094;</div>
        <div class="modal-nav nav-next" onclick="nextImg(event)">&#10095;</div>
        <div class="modal-center-container">
            <div class="modal-main-unit">
                <div id="modal-counter" class="modal-counter" style="color:white; background:rgba(0,0,0,0.8); border-radius:20px; margin-bottom:10px; display:inline-block; padding:2px 15px;"></div>
                <img class="modal-content" id="modal-img">
            </div>
        </div>
    `;
    
    const modalImg = document.getElementById('modal-img');
    const counterElem = document.getElementById('modal-counter');
    if (currentImages.length > 0) {
        counterElem.innerText = `${currentIndex + 1} / ${currentImages.length}`;
        counterElem.style.display = "block";
    }

    modal.style.display = "block";
    modalImg.src = imgUrl;

    // 💡 重要：位置指定（style.width 等）をすべて消去
    modalImg.onload = function() {
        modalImg.oncontextmenu = () => false;
    };

    modal.setAttribute('data-current-name', name);
    modal.setAttribute('data-current-price', price);
    modal.setAttribute('data-current-url', imgUrl);
    modal.onclick = function(e) { if(e.target.id === 'pos-modal' || e.target.className === 'modal-center-container') closeModal(); };
}

function addCurrentToCart(e) {
    if (e) e.stopPropagation();
    const modal = document.getElementById('pos-modal');
    const name = modal.getAttribute('data-current-name');
    const priceText = modal.getAttribute('data-current-price');
    const url = modal.getAttribute('data-current-url');
    const price = parseInt(priceText.replace(/[^0-9]/g, '')) || 0;
    cart.push({name: name, price: price, url: url});
    localStorage.setItem('pos_cart_data', JSON.stringify(cart));
    renderCart();
    const btn = document.getElementById('modal-add-btn');
    btn.innerText = "✅ 追加しました！";
    if (currentImages.length > 1 && currentIndex < currentImages.length - 1) setTimeout(nextImg, 300);
    else setTimeout(closeModal, 500);
}

function closeModal() {
    const modal = document.getElementById('pos-modal');
    if (modal) modal.style.display = "none";
    currentImages = [];
}

function nextImg(e) {
    if (e) e.stopPropagation();
    if (currentImages.length === 0) return;
    currentIndex = (currentIndex + 1) % currentImages.length;
    openCarousel(currentImages[currentIndex].url, currentImages[currentIndex].name, currentImages[currentIndex].price);
}

function prevImg(e) {
    if (e) e.stopPropagation();
    if (currentImages.length === 0) return;
    currentIndex = (currentIndex - 1 + currentImages.length) % currentImages.length;
    openCarousel(currentImages[currentIndex].url, currentImages[currentIndex].name, currentImages[currentIndex].price);
}

function getRowData(row) {
    const nameCell = row.querySelector('.column-display_name_jp div') || row.querySelector('.column-display_name div') || row.cells[1];
    const imgCell = row.querySelector('.column-display_image_jp img') || row.querySelector('.column-display_image img') || row.cells[2].querySelector('img');
    const priceCell = row.querySelector('.column-display_price_jp div') || row.querySelector('.column-display_price div') || row.cells[3];
    return { url: imgCell ? imgCell.src : '', name: nameCell ? nameCell.innerText.trim() : '不明', price: priceCell ? priceCell.innerText.trim() : '0' };
}

function bulkCarousel() {
    const selected = document.querySelectorAll('#result_list tbody input.action-select:checked');
    if (selected.length === 0) return;
    currentImages = Array.from(selected).map(cb => getRowData(cb.closest('tr')));
    currentIndex = 0;
    openCarousel(currentImages[0].url, currentImages[0].name, currentImages[0].price);
}

function bulkAddToCart() {
    const selected = document.querySelectorAll('#result_list tbody input.action-select:checked');
    if (selected.length === 0) return;
    selected.forEach(cb => {
        const data = getRowData(cb.closest('tr'));
        cart.push({name: data.name, price: parseInt(data.price.replace(/[^0-9]/g, '')) || 0, url: data.url});
        cb.checked = false;
    });
    localStorage.setItem('pos_cart_data', JSON.stringify(cart));
    renderCart();
}

let cart = JSON.parse(localStorage.getItem('pos_cart_data')) || [];
function renderCart() {
    let cartPopup = document.getElementById('cart-popup');
    if (!cartPopup) {
        cartPopup = document.createElement('div');
        cartPopup.id = 'cart-popup';
        cartPopup.style = "position:fixed; bottom:20px; right:20px; width:280px; background:#111; color:white; padding:15px; border-radius:10px; z-index:9999; border:1px solid #444; box-shadow:0 10px 30px rgba(0,0,0,0.5);";
        document.body.appendChild(cartPopup);
    }
    const total = cart.reduce((sum, item) => sum + item.price, 0);
    cartPopup.innerHTML = `<h3>🛒 カート合計</h3><ul id="cart-list" style="margin:0; padding:0; list-style:none; max-height:220px; overflow-y:auto;">${cart.map((item, index) => `<li style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; font-size:12px; border-bottom:1px solid #222; padding-bottom:5px;"><div style="display:flex; align-items:center; gap:8px; flex:1; overflow:hidden;"><img src="${item.url}" style="width:35px; height:35px; object-fit:cover; border-radius:3px;"><div style="display:flex; flex-direction:column; overflow:hidden;"><span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-weight:bold;">${item.name}</span><span style="color:#ffcc00;">¥${item.price.toLocaleString()}</span></div></div><button onclick="removeFromCart(${index})" style="background:transparent; color:#ff4444; border:none; cursor:pointer; font-size:16px; padding:0 5px; font-weight:bold;">×</button></li>`).join('')}</ul><div style="margin-top:10px; border-top:1px solid #333; padding-top:8px; display:flex; justify-content:space-between; font-weight:bold;"><span>合計:</span><span>¥${total.toLocaleString()}</span></div><button onclick="checkout()" style="width:100%; margin-top:10px; background:#28a745; color:white; border:none; padding:12px; cursor:pointer; border-radius:4px; font-weight:bold; font-size:16px;">✨ 会計確定</button><button onclick="clearCart()" style="width:100%; margin-top:10px; background:#333; color:white; border:none; padding:8px; cursor:pointer; border-radius:4px; font-size:12px;">リセット</button>`;
    cartPopup.style.display = cart.length > 0 ? 'block' : 'none';
}
async function checkout() {
    if (cart.length === 0) return;
    if (!confirm("お会計を確定してお迎えしますか？")) return;
    try {
        const response = await fetch('/admin/record-sale/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') }, body: JSON.stringify({ items: cart }) });
        if (response.ok) { alert("💖 お迎え完了しました！"); cart = []; localStorage.removeItem('pos_cart_data'); renderCart(); }
    } catch (error) { alert("通信エラー: " + error); }
}
function removeFromCart(index) { cart.splice(index, 1); localStorage.setItem('pos_cart_data', JSON.stringify(cart)); renderCart(); }
function clearCart() { if(confirm("カートをリセットしますか？")) { cart = []; localStorage.removeItem('pos_cart_data'); renderCart(); } }
function getCookie(name) { let v = null; if (document.cookie && document.cookie !== '') { const cookies = document.cookie.split(';'); for (let i = 0; i < cookies.length; i++) { const c = cookies[i].trim(); if (c.substring(0, name.length + 1) === (name + '=')) { v = decodeURIComponent(c.substring(name.length + 1)); break; } } } return v; }
document.addEventListener('DOMContentLoaded', () => renderCart());
// Movement Form Handler
let movementId = CONFIG.pendingMovementId;
let items = CONFIG.pendingItems || [];
let itemsCount = items.length;
let selectedProduct = null;
let turboMode = false;
let soundEnabled = true;
let ignoreStock = false;

// Sound Manager (Web Audio API)
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
function beep(freq = 520, duration = 200, type = 'sine') {
    if (!soundEnabled) return;
    try {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = type;
        osc.frequency.value = freq;
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        setTimeout(() => osc.stop(), duration);
    } catch (e) { console.error('Audio error', e); }
}

const SOUNDS = {
    SUCCESS: () => beep(880, 100, 'sine'), // High pitch
    ERROR: () => { beep(200, 300, 'sawtooth'); setTimeout(() => beep(200, 300, 'sawtooth'), 400); }, // Low buzz
    VERIFIED: () => { beep(440, 150); setTimeout(() => beep(554, 150), 150); setTimeout(() => beep(659, 300), 300); } // Major chord
};

document.addEventListener('DOMContentLoaded', () => {
    initSettings();
    initQRInput();
    initModal();
    initActions();
    renderItems();
    updateUI();
});

function initSettings() {
    const turboCheck = document.getElementById('turbo-mode');
    const soundCheck = document.getElementById('sound-mode');

    // Load saved settings
    turboMode = localStorage.getItem('turboMode') === 'true';
    soundEnabled = localStorage.getItem('soundEnabled') !== 'false'; // Default true

    if (turboCheck) {
        turboCheck.checked = turboMode;
        turboCheck.addEventListener('change', (e) => {
            turboMode = e.target.checked;
            localStorage.setItem('turboMode', turboMode);
        });
    }

    if (soundCheck) {
        soundCheck.checked = soundEnabled;
        soundCheck.addEventListener('change', (e) => {
            soundEnabled = e.target.checked;
            localStorage.setItem('soundEnabled', soundEnabled);
        });
    }

    // Ignore Stock setting
    const ignoreStockCheck = document.getElementById('ignore-stock');
    ignoreStock = localStorage.getItem('ignoreStock') === 'true';

    if (ignoreStockCheck) {
        ignoreStockCheck.checked = ignoreStock;
        ignoreStockCheck.addEventListener('change', (e) => {
            ignoreStock = e.target.checked;
            localStorage.setItem('ignoreStock', ignoreStock);
        });
    }

    // Discard Button Logic
    const discardBtn = document.getElementById('discard-pending-btn');
    if (discardBtn) {
        discardBtn.addEventListener('click', async () => {
            if (confirm('Eski harakatni bekor qilib yangisini boshlaysizmi?')) {
                await createMovement(true); // true = force new
            }
        });
    }
}

// QR Scanner Input
function initQRInput() {
    const qrInput = document.getElementById('qr-input');
    if (!qrInput) return;

    // Keep focus
    qrInput.addEventListener('blur', () => {
        setTimeout(() => qrInput.focus(), 100);
    });

    // Handle Enter
    qrInput.addEventListener('keypress', async (e) => {
        if (e.key !== 'Enter') return;
        e.preventDefault();

        const barcode = qrInput.value.trim();
        qrInput.value = '';

        if (!barcode) return;

        await lookupProduct(barcode);
        qrInput.focus();
    });
}

async function lookupProduct(barcode) {
    try {
        const resp = await fetch(`${CONFIG.urls.productByBarcode}?q=${encodeURIComponent(barcode)}`);
        const data = await resp.json();

        if (data.found) {
            selectedProduct = data.product;
            SOUNDS.SUCCESS();

            if (turboMode) {
                // Direct add in Turbo Mode
                await confirmAddItem(1);
                showToast('qr-success', `⚡ Qo'shildi: ${data.product.name}`, 'success');
            } else {
                showQtyModal();
                showToast('qr-success', `✅ ${data.product.name}`, 'success');
            }
        } else {
            SOUNDS.ERROR();
            showToast('qr-error', data.error || 'QR topilmadi', 'error');
        }
    } catch (err) {
        SOUNDS.ERROR();
        showToast('qr-error', 'Server xatosi', 'error');
    }
}

// Quantity Modal
function initModal() {
    const modal = document.getElementById('qty-modal');
    if (!modal) return;

    document.getElementById('modal-cancel').addEventListener('click', hideModal);
    document.getElementById('modal-confirm').addEventListener('click', () => confirmAddItem());

    // Enter to confirm in modal
    document.getElementById('qty-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') confirmAddItem();
    });
}

function showQtyModal() {
    const modal = document.getElementById('qty-modal');
    const info = document.getElementById('modal-product-info');
    const qtyInput = document.getElementById('qty-input');

    info.innerHTML = `
        <p><strong>${selectedProduct.name}</strong></p>
        <p>SKU: ${selectedProduct.sku} | Zaxira: ${selectedProduct.stock_qty} ${selectedProduct.unit}</p>
    `;

    qtyInput.value = 1;
    qtyInput.max = CONFIG.movementType === 'OUT' ? selectedProduct.stock_qty : 99999;

    modal.classList.remove('hidden');
    qtyInput.focus();
    qtyInput.select();
}

function hideModal() {
    document.getElementById('qty-modal').classList.add('hidden');
    selectedProduct = null;
    document.getElementById('qr-input').focus();
}

async function confirmAddItem(directQty = null) {
    if (!selectedProduct) return;

    let quantity = directQty;
    let unitPrice = 0;

    if (quantity === null) {
        quantity = parseInt(document.getElementById('qty-input').value) || 1;
        unitPrice = parseFloat(document.getElementById('price-input').value) || 0;
    }

    if (quantity <= 0) {
        if (!directQty) alert('Miqdor 0 dan katta bo\'lishi kerak');
        return;
    }

    // Show warning for OUT if stock is low (non-blocking) - skip if ignoreStock is enabled
    if (!ignoreStock && CONFIG.movementType === 'OUT' && quantity > selectedProduct.stock_qty) {
        showToast('qr-error', `⚠️ Diqqat: Zaxira kam (mavjud: ${selectedProduct.stock_qty}). Minusga o'tadi.`, 'error');
    }

    // Ensure movement exists
    if (!movementId) {
        await createMovement();
    }

    // Add item
    try {
        const url = CONFIG.urls.addItem.replace('{id}', movementId);
        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.csrfToken
            },
            body: JSON.stringify({
                product_id: selectedProduct.id,
                quantity: quantity,
                unit_price: unitPrice
            })
        });

        const data = await resp.json();

        if (data.ok) {
            // Add to local list
            const existingIdx = items.findIndex(i => i.productId === selectedProduct.id);
            if (existingIdx >= 0) {
                items[existingIdx].quantity = data.total_quantity;
            } else {
                items.push({
                    id: data.item_id,
                    productId: selectedProduct.id,
                    name: selectedProduct.name,
                    sku: selectedProduct.sku,
                    quantity: data.total_quantity,
                    unit: selectedProduct.unit,
                    stockQty: selectedProduct.stock_qty
                });
            }
            itemsCount = items.length;
            renderItems();
            updateUI();
            if (!directQty) hideModal();
        } else {
            SOUNDS.ERROR();
            if (!directQty) alert(data.error || 'Xato');
            else showToast('qr-error', data.error, 'error');
        }
    } catch (err) {
        SOUNDS.ERROR();
        if (!directQty) alert('Server xatosi: ' + err.message);
    }
}

async function createMovement(forceNew = false) {
    try {
        const resp = await fetch(CONFIG.urls.createMovement, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.csrfToken
            },
            body: JSON.stringify({
                movement_type: CONFIG.movementType,
                note: forceNew ? 'Force restart' : ''
            })
        });

        const data = await resp.json();
        if (data.ok) {
            movementId = data.movement_id;
            if (forceNew) window.location.reload();
        } else {
            throw new Error(data.error);
        }
    } catch (err) {
        alert('Movement yaratib bo\'lmadi: ' + err.message);
        throw err;
    }
}

// Items Table
function renderItems() {
    const tbody = document.getElementById('items-body');
    const emptyMsg = document.getElementById('empty-message');

    if (!tbody) return;

    if (items.length === 0) {
        tbody.innerHTML = '';
        if (emptyMsg) emptyMsg.classList.remove('hidden');
        return;
    }

    if (emptyMsg) emptyMsg.classList.add('hidden');

    tbody.innerHTML = items.map(item => `
        <tr data-id="${item.id}">
            <td>${item.name}</td>
            <td><code>${item.sku}</code></td>
            <td>${item.quantity}</td>
            <td>${item.unit}</td>
            <td>${item.stockQty}</td>
            <td>
                <button type="button" class="btn btn-sm btn-danger remove-btn" data-id="${item.id}">
                    ✕
                </button>
            </td>
        </tr>
    `).join('');

    // Add remove handlers
    tbody.querySelectorAll('.remove-btn').forEach(btn => {
        btn.addEventListener('click', () => removeItem(parseInt(btn.dataset.id)));
    });
}

async function removeItem(itemId) {
    if (!movementId) return;

    try {
        const url = CONFIG.urls.removeItem
            .replace('{id}', movementId)
            .replace('{item_id}', itemId);

        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': CONFIG.csrfToken
            }
        });

        const data = await resp.json();

        if (data.ok) {
            items = items.filter(i => i.id !== itemId);
            itemsCount = items.length;
            renderItems();
            updateUI();
        } else {
            alert(data.error || 'Xato');
        }
    } catch (err) {
        alert('Xato: ' + err.message);
    }
}

// Actions
function initActions() {
    const finalizeBtn = document.getElementById('finalize-btn');
    const cancelBtn = document.getElementById('cancel-btn');

    if (finalizeBtn) {
        finalizeBtn.addEventListener('click', finalizeMovement);
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', cancelMovement);
    }
}

async function finalizeMovement() {
    if (!movementId) {
        alert('Movement topilmadi');
        return;
    }

    if (itemsCount === 0) {
        SOUNDS.ERROR();
        alert('Mahsulot qo\'shing');
        return;
    }

    if (!faceVerified) {
        SOUNDS.ERROR();
        alert('Face ID tasdiqlanmagan');
        return;
    }

    try {
        const url = CONFIG.urls.finalize.replace('{id}', movementId);
        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': CONFIG.csrfToken
            }
        });

        const data = await resp.json();

        if (data.ok) {
            SOUNDS.VERIFIED();
            alert(data.message || 'Muvaffaqiyatli yakunlandi');
            window.location.href = '/movements/';
        } else {
            SOUNDS.ERROR();
            alert(data.error || 'Xato');
        }
    } catch (err) {
        SOUNDS.ERROR();
        alert('Xato: ' + err.message);
    }
}

async function cancelMovement() {
    if (!movementId) {
        window.location.reload();
        return;
    }

    if (!confirm('Harakatni bekor qilmoqchimisiz?')) return;

    try {
        const url = CONFIG.urls.cancel.replace('{id}', movementId);
        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': CONFIG.csrfToken
            }
        });

        const data = await resp.json();

        if (data.ok) {
            window.location.reload();
        } else {
            alert(data.error || 'Xato');
        }
    } catch (err) {
        alert('Xato: ' + err.message);
    }
}

function updateUI() {
    const finalizeBtn = document.getElementById('finalize-btn');
    if (finalizeBtn) {
        finalizeBtn.disabled = !(movementId && itemsCount > 0 && faceVerified);
    }
}

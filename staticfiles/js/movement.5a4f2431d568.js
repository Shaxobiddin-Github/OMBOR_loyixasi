// Movement Form Handler
let movementId = CONFIG.pendingMovementId;
let items = CONFIG.pendingItems || [];
let itemsCount = items.length;
let selectedProduct = null;
let turboMode = false;
let soundEnabled = true;
let ignoreStock = false;

// faceVerified is already declared in face_capture.js
if (typeof CONFIG !== 'undefined' && CONFIG.faceVerified) {
    faceVerified = true;
}

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
    initTargetSelect();
    initActions();
    renderItems();
    updateUI();

    // Check initial state
    if (faceVerified) {
        unlockScanner();
    }

    // Listen for Face ID events
    document.addEventListener('face-verified', (e) => {
        faceVerified = true;
        unlockScanner();
        // If we have a target select, we might want to update it based on the verified user?
        // But backend handles permission checks. 
        // We could just refresh the page or update UI state.
    });

    document.addEventListener('face-validation-failed', () => {
        faceVerified = false;
        lockScanner();
    });
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

// Lock/Unlock Scanner
function unlockScanner() {
    const card = document.getElementById('scanner-card');
    const input = document.getElementById('qr-input');

    if (card) card.classList.remove('locked');
    if (input) {
        input.disabled = false;
        input.focus();
    }
}

function lockScanner() {
    const card = document.getElementById('scanner-card');
    const input = document.getElementById('qr-input');

    if (card) card.classList.add('locked');
    if (input) {
        input.disabled = true;
        input.value = '';
    }
}

// QR Scanner Input
function initQRInput() {
    const qrInput = document.getElementById('qr-input');
    if (!qrInput) return;

    // Keep focus
    qrInput.addEventListener('blur', () => {
        if (!faceVerified) return; // Don't force focus if locked
        setTimeout(() => {
            // Check again in case state changed or modal opened
            const modal = document.getElementById('qty-modal');
            if (modal && !modal.classList.contains('hidden')) return;
            if (faceVerified) qrInput.focus();
        }, 100);
    });

    // Handle Enter
    qrInput.addEventListener('keypress', async (e) => {
        if (e.key !== 'Enter') return;
        e.preventDefault();

        if (!faceVerified) return;

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

            // Auto-switch target for IN if Commander
            if (CONFIG.movementType === 'IN' && data.product.assigned_to) {
                const currentUser = CONFIG.employees.find(e => e.id == CONFIG.userEmployeeId);
                const isCommander = currentUser && currentUser.is_commander;

                if (isCommander && targetEmployeeId != data.product.assigned_to.id) {
                    const select = document.getElementById('target-select');
                    // Check if the assigned employee is in the list
                    const optionExists = Array.from(select.options).some(o => o.value == data.product.assigned_to.id);

                    if (optionExists) {
                        select.value = data.product.assigned_to.id;
                        targetEmployeeId = data.product.assigned_to.id;
                        showToast('qr-success', `🔀 Buyurtmachi o'zgardi: ${data.product.assigned_to.name}`, 'success');
                    }
                }
            }

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
                unit_price: unitPrice,
                target_employee_id: targetEmployeeId // Send current selection
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

// Target Select Logic
let targetEmployeeId = null;

function initTargetSelect() {
    const section = document.getElementById('target-section');
    const select = document.getElementById('target-select');

    // Only for IN movement
    if (CONFIG.movementType !== 'IN') return;

    // Show section if any employees exist (should always be true)
    section.style.display = 'block';
    select.innerHTML = ''; // Clear existing

    // Determine permissions with loose equality
    const currentUserId = CONFIG.userEmployeeId;
    const currentUser = CONFIG.employees.find(e => e.id == currentUserId);
    const isCommander = currentUser ? currentUser.is_commander : false;

    // Populate
    let count = 0;
    CONFIG.employees.forEach(emp => {
        let canSee = false;
        // 1. I can always see myself
        if (emp.id == currentUserId) canSee = true;
        // 2. Commander can see everyone
        else if (isCommander) canSee = true;

        if (canSee) {
            const opt = document.createElement('option');
            opt.value = emp.id;
            const isMe = (emp.id == currentUserId);
            opt.textContent = emp.name + (isMe ? " (Men o'zim)" : "");
            select.appendChild(opt);
            count++;
        }
    });

    // Fallback: If list is empty (e.g. user not found), at least show a placeholder or try to show self from ID?
    if (count === 0 && currentUserId) {
        const opt = document.createElement('option');
        opt.value = currentUserId;
        opt.textContent = "Men o'zim";
        select.appendChild(opt);
    }

    // 3. Set Default or Pending Target
    if (movementId && itemsCount > 0) {
        select.disabled = true; // Lock if items exist
    } else {
        select.disabled = false;
    }

    // Set initial value
    if (!targetEmployeeId) {
        targetEmployeeId = currentUserId;
        select.value = currentUserId;
    }

    select.addEventListener('change', () => {
        targetEmployeeId = select.value ? parseInt(select.value) : null;
    });
}

// Call initTargetSelect in DOMContentLoaded... added to main list below:

// ─────────────────────────────────────────────

async function createMovement(forceNew = false) {
    // Collect data
    const body = {
        movement_type: CONFIG.movementType,
        note: forceNew ? 'Force restart' : '',
        force_new: forceNew
    };

    // Prepare target
    const select = document.getElementById('target-select');
    if (select && select.value) {
        body.target_employee_id = parseInt(select.value);
    }

    try {
        const resp = await fetch(CONFIG.urls.createMovement, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.csrfToken
            },
            body: JSON.stringify(body)
        });

        const data = await resp.json();
        if (data.ok) {
            movementId = data.movement_id;

            // Disable target select once movement created
            if (select) select.disabled = true;

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
    const bulkOutBtn = document.getElementById('bulk-out-btn');

    if (finalizeBtn) {
        finalizeBtn.addEventListener('click', finalizeMovement);
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', cancelMovement);
    }

    if (bulkOutBtn) {
        bulkOutBtn.addEventListener('click', bulkOutAll);
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

    const btn = document.getElementById('finalize-btn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = '⏳ Yakunlanmoqda...';
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
            // showToast('success', '✅ Muvaffaqiyatli yakunlandi'); // movement.js doesn't have showToast helper globally? 
            // It seems movement.js used alert() in previous code. 
            // But let's check if showToast exists? 
            // The file I read (step 124) has showToast calls! e.g. line 136.
            showToast('qr-success', '✅ Muvaffaqiyatli yakunlandi!', 'success');

            // ──────────────────────────────────────────
            // SHOW RESULT (Pseudo-Step 3)
            // ──────────────────────────────────────────
            const tbody = document.getElementById('items-body');
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="6" style="text-align:center; padding: 30px;">
                            <h2 style="color: #10b981;">✅ Yakunlandi</h2>
                            <p>${data.message || 'Muvaffaqiyatli saqlandi'}</p>
                            <p style="color: #64748b; font-size: 0.9em;">3 soniyadan so'ng yangilanadi...</p>
                        </td>
                    </tr>
                `;
            }

            // Hide buttons
            if (btn) btn.style.display = 'none';
            const cancelBtn = document.getElementById('cancel-btn');
            if (cancelBtn) cancelBtn.style.display = 'none';

            // ──────────────────────────────────────────
            // DELAYED FULL RESET (3-5s)
            // ──────────────────────────────────────────
            setTimeout(() => {
                resetUI();
            }, 3000);

        } else {
            SOUNDS.ERROR();
            alert(data.error || 'Xato');
        }
    } catch (err) {
        SOUNDS.ERROR();
        alert('Xato: ' + err.message);
    } finally {
        if (btn) {
            btn.disabled = false; // updateUI will likely disable it anyway
            btn.textContent = '✅ Yakunlash';
            updateUI();
        }
    }
}

// Alias for face_capture.js compatibility
function updateFinalizeButton() {
    updateUI();
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
        if (finalizeBtn.style.display !== 'none') {
            finalizeBtn.disabled = !(movementId && itemsCount > 0 && faceVerified);
        }
    }
}

function resetUI() {
    // 1. Reset Data
    movementId = null;
    items = [];
    itemsCount = 0;
    faceVerified = false;
    lockScanner(); // Ensure scanner is locked

    // 2. Reset Tables & Counters
    renderItems();

    // 3. Reset Target Select
    const targetSelect = document.getElementById('target-select');
    if (targetSelect) {
        targetSelect.value = "";
        targetSelect.disabled = false;
    }

    // 4. Reset Face ID UI
    if (typeof updateFaceStatus === 'function') {
        updateFaceStatus(false, 'Face tasdiqlanmagan');
    }

    // 5. Update Buttons
    const btn = document.getElementById('finalize-btn');
    if (btn) {
        btn.style.display = 'inline-block';
        btn.disabled = false; // updateUI will fix this
        btn.textContent = '✅ Yakunlash';
    }
    updateUI();

    // 6. Reset Input
    const qrInput = document.getElementById('qr-input');
    if (qrInput) {
        qrInput.value = '';
        // qrInput.focus(); // Don't focus if locked
    }
}

// Bulk Out All Stock
async function bulkOutAll() {
    // Double confirmation for safety
    if (!confirm('⚠️ DIQQAT!\n\nOmbordagi BARCHA mahsulotlar chiqariladi.\nBarcha zaxira 0 ga tushadi.\n\nDavom etasizmi?')) {
        return;
    }
    if (!confirm('🚨 YAKUNIY TASDIQLASH\n\nRostdan ham BARCHA mahsulotlarni chiqarib yubormochimisiz?\n\nBu amalni bekor qilib bo\'lmaydi!')) {
        return;
    }

    const bulkBtn = document.getElementById('bulk-out-btn');
    if (bulkBtn) {
        bulkBtn.disabled = true;
        bulkBtn.textContent = '⏳ Yuklanmoqda...';
    }

    try {
        const resp = await fetch(CONFIG.urls.bulkOutAll, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.csrfToken
            }
        });

        const data = await resp.json();

        if (data.ok) {
            // Update local state with server response
            movementId = data.movement_id;
            items = data.items;
            itemsCount = items.length;

            renderItems();
            updateUI();

            SOUNDS.SUCCESS();
            showToast('qr-success', `✅ ${data.message}`, 'success');

            // Hide the bulk button after successful load
            if (bulkBtn) {
                bulkBtn.style.display = 'none';
            }
        } else {
            SOUNDS.ERROR();
            alert(data.error || 'Xatolik yuz berdi');
            if (bulkBtn) {
                bulkBtn.disabled = false;
                bulkBtn.textContent = '🚨 Barchasini chiqarish (ombor bo\'shatish)';
            }
        }
    } catch (err) {
        SOUNDS.ERROR();
        alert('Server xatosi: ' + err.message);
        if (bulkBtn) {
            bulkBtn.disabled = false;
            bulkBtn.textContent = '🚨 Barchasini chiqarish (ombor bo\'shatish)';
        }
    }
}

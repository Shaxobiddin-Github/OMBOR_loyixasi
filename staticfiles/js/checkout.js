/**
 * Checkout.js — Toifa asosidagi chiqish (OUT) logikasi.
 * 
 * Jarayon (Revamped Batch Flow):
 * 1. Face ID → actor (Employee) aniqlanadi
 * 2. Komandir bo'lsa → boshqa xodimni tanlash mumkin (target)
 * 3. QR scan → checkout_standard (ADD TO PENDING LIST)
 * 4. "Yakunlash" tugmasi → finalize_movement (SAVE & DEDUCT STOCK)
 * 5. "Bekor qilish" tugmasi → cancel_movement (CLEAR LIST)
 */

// ── State ──
let actor = null;           // Face ID orqali aniqlangan xodim
let targetEmployeeId = null; // Komandir tanlagan maqsadli xodim (null = o'zi)
let faceVerified = false;
let turboMode = false;
let soundEnabled = true;
let checkoutHistory = [];    // Chiqarilayotgan mahsulotlar (Pending)
let currentMovementId = null; // Backend ID for pending movement

// ── Audio ──
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
    SUCCESS: () => beep(880, 100, 'sine'),
    ERROR: () => { beep(200, 300, 'sawtooth'); setTimeout(() => beep(200, 300, 'sawtooth'), 400); },
    VERIFIED: () => { beep(440, 150); setTimeout(() => beep(554, 150), 150); setTimeout(() => beep(659, 300), 300); }
};

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
    initCamera();
    initCaptureButton();
    initQRInput();
    initEmergencyButton();
    initTargetSelect();
    initModal();
    initSettings();
    initActionButtons(); // New: Finalize/Cancel logic
    checkFaceStatus();

    // Check if there's already a pending movement on load
    if (CONFIG.pendingMovementId) {
        currentMovementId = CONFIG.pendingMovementId;
        if (CONFIG.pendingItems && CONFIG.pendingItems.length > 0) {
            checkoutHistory = CONFIG.pendingItems.map(item => ({
                id: item.id,
                name: item.name,
                sku: item.sku,
                quantity: item.quantity
            }));
            renderResults();
            setStep(3);
        }
    }
});

// ════════════════════════════════════════════
// Camera & Face ID
// ════════════════════════════════════════════
let video, canvas, ctx;

function initCamera() {
    video = document.getElementById('video');
    canvas = document.getElementById('canvas');
    if (!video || !canvas) return;
    ctx = canvas.getContext('2d');

    navigator.mediaDevices.getUserMedia({
        video: { width: 240, height: 180, facingMode: 'user' }
    }).then(stream => {
        video.srcObject = stream;
    }).catch(err => {
        console.error('Kamera xatosi:', err);
    });
}

function initCaptureButton() {
    const btn = document.getElementById('capture-btn');
    if (btn) btn.addEventListener('click', captureFace);
}

async function captureFace() {
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);

    try {
        const resp = await fetch(CONFIG.urls.faceVerify, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.csrfToken
            },
            body: JSON.stringify({ image: dataUrl })
        });
        const data = await resp.json();

        if (data.ok) {
            SOUNDS.VERIFIED();
            // Now fetch full status with categories
            await checkFaceStatus();
        } else {
            SOUNDS.ERROR();
            updateFaceUI(false, data.error || 'Yuz tanilmadi');
        }
    } catch (err) {
        SOUNDS.ERROR();
        updateFaceUI(false, 'Server xatosi: ' + err.message);
    }
}

async function checkFaceStatus() {
    try {
        const resp = await fetch(CONFIG.urls.faceStatus);
        const data = await resp.json();

        if (data.verified) {
            faceVerified = true;
            actor = {
                id: data.employee_id,
                name: data.name,
                confidence: data.confidence,
                is_commander: data.is_commander,
                categories: data.categories || [],
            };
            updateFaceUI(true, `✅ ${data.name} (${data.confidence})`);
            showEmployeeBadge();
            unlockScanner();

            // If we have items but facial verification was lost/expired, re-enabling it allows continuing
            if (checkoutHistory.length > 0) {
                setStep(3);
            } else {
                setStep(2);
            }
        }
    } catch (err) {
        console.error('Face status check failed:', err);
    }
}

function updateFaceUI(verified, message) {
    const el = document.getElementById('face-status');
    if (!el) return;
    el.className = 'face-status ' + (verified ? 'verified' : 'pending');
    el.innerHTML = verified
        ? `✅ ${message}`
        : `❌ ${message}`;
}

function showEmployeeBadge() {
    if (!actor) return;

    const badge = document.getElementById('employee-badge');
    const nameEl = document.getElementById('emp-name');
    const metaEl = document.getElementById('emp-meta');
    const catsEl = document.getElementById('emp-categories');

    nameEl.innerHTML = actor.name +
        (actor.is_commander ? '<span class="commander-tag">⭐ KOMANDIR</span>' : '');
    metaEl.textContent = `Ishonch: ${actor.confidence}`;

    catsEl.innerHTML = actor.categories.map(c =>
        `<span class="cat-tag">${c.name}</span>`
    ).join('');

    badge.classList.add('visible');

    // Show commander target select
    if (actor.is_commander) {
        showTargetSelect();
    }
}

// ════════════════════════════════════════════
// Commander Target Select
// ════════════════════════════════════════════
function showTargetSelect() {
    const section = document.getElementById('target-section');
    const select = document.getElementById('target-select');
    if (!section || !select) return;

    // Clear and populate only if empty (preserve selection if page reloaded with state)
    if (select.children.length <= 1) {
        select.innerHTML = '<option value="">— O\'zim uchun —</option>';
        CONFIG.employees.forEach(emp => {
            if (emp.id !== actor.id) {
                const cats = emp.categories.map(c => c.name).join(', ');
                const opt = document.createElement('option');
                opt.value = emp.id;
                opt.textContent = `${emp.name} (${emp.employee_id}) — ${cats || 'toifasiz'}`;
                select.appendChild(opt);
            }
        });
    }

    section.classList.add('visible');
}

function initTargetSelect() {
    const select = document.getElementById('target-select');
    if (!select) return;

    select.addEventListener('change', () => {
        // Prevent changing target if Items exist
        if (checkoutHistory.length > 0) {
            if (!confirm("Diqqat! Ro'yxatdagi mahsulotlar tozalanadi. Davom etasizmi?")) {
                // Revert change
                select.value = targetEmployeeId || "";
                return;
            }
            // Caller should handle clearing via discard if backend requires it, 
            // but here we just reset frontend list and let backend handle new target on next scan?
            // Actually, backend blocks target switch if items exist.
            // So we should ideally clear the backend list too.
            cancelCheckout(true); // Silent cancel to clear list
        }

        targetEmployeeId = select.value ? parseInt(select.value) : null;

        // Show target categories
        const catsDiv = document.getElementById('target-categories');
        if (targetEmployeeId) {
            const emp = CONFIG.employees.find(e => e.id === targetEmployeeId);
            if (emp && catsDiv) {
                catsDiv.innerHTML = emp.categories.map(c =>
                    `<span class="cat-tag">${c.name}</span>`
                ).join('');
            }
        } else if (catsDiv) {
            catsDiv.innerHTML = '';
        }
    });
}

// ════════════════════════════════════════════
// Scanner Lock/Unlock
// ════════════════════════════════════════════
function unlockScanner() {
    const card = document.getElementById('scanner-card');
    const input = document.getElementById('qr-input');
    const emergBtn = document.getElementById('emergency-btn');

    if (card) card.classList.remove('locked');
    if (input) { input.disabled = false; input.focus(); }
    if (emergBtn) emergBtn.disabled = false;
}

function setStep(n) {
    for (let i = 1; i <= 3; i++) {
        const el = document.getElementById(`step-${i}`);
        if (!el) continue;
        el.classList.remove('active', 'done');
        if (i < n) el.classList.add('done');
        else if (i === n) el.classList.add('active');
    }
}

// ════════════════════════════════════════════
// QR Scanner → Standard Checkout
// ════════════════════════════════════════════
let selectedProduct = null;

function initQRInput() {
    const qrInput = document.getElementById('qr-input');
    if (!qrInput) return;

    // Keep focus (but not when dropdown or modal is active)
    qrInput.addEventListener('blur', () => {
        setTimeout(() => {
            const modal = document.getElementById('qty-modal');
            const targetSelect = document.getElementById('target-select');
            if (modal && !modal.classList.contains('hidden')) return;
            if (document.activeElement === targetSelect) return;
            qrInput.focus();
        }, 300);
    });

    qrInput.addEventListener('keypress', async (e) => {
        if (e.key !== 'Enter') return;
        e.preventDefault();
        const barcode = qrInput.value.trim();
        qrInput.value = '';
        if (!barcode || !faceVerified) return;
        await lookupProduct(barcode);
    });
}

async function lookupProduct(barcode) {
    const statusEl = document.getElementById('scan-status');
    try {
        const resp = await fetch(`${CONFIG.urls.productByBarcode}?q=${encodeURIComponent(barcode)}`);
        const data = await resp.json();

        if (data.found) {
            selectedProduct = data.product;
            SOUNDS.SUCCESS();

            if (turboMode) {
                if (statusEl) statusEl.innerHTML = `⚡ <b>${data.product.name}</b> — turbo qo'shish...`;
                // TARGET logic happens in checkout endpoint, no need to switch here unless needed for UI
                await doStandardCheckoutDirect(1);
            } else {
                if (statusEl) statusEl.innerHTML = `✅ <b>${data.product.name}</b> topildi — miqdor kiriting`;

                // Note: we don't auto-switch target blindly here because user might be adding to existing list

                showQtyModal();
            }
        } else {
            SOUNDS.ERROR();
            if (statusEl) statusEl.innerHTML = `❌ "${barcode}" topilmadi`;
            showToast('error', data.error || 'Mahsulot topilmadi');
        }
    } catch (err) {
        SOUNDS.ERROR();
        if (statusEl) statusEl.innerHTML = '❌ Server xatosi';
    }
}

// ════════════════════════════════════════════
// Quantity Modal
// ════════════════════════════════════════════
function initModal() {
    const modal = document.getElementById('qty-modal');
    if (!modal) return;

    document.getElementById('modal-cancel').addEventListener('click', hideModal);
    document.getElementById('modal-confirm').addEventListener('click', () => doStandardCheckout());
    document.getElementById('qty-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') doStandardCheckout();
    });
}

function showQtyModal() {
    const modal = document.getElementById('qty-modal');
    const info = document.getElementById('modal-product-info');
    const qtyInput = document.getElementById('qty-input');
    if (!modal || !selectedProduct) return;

    info.innerHTML = `
        <p><strong>${selectedProduct.name}</strong></p>
        <p style="color:#64748b;font-size:0.9em;">
            SKU: ${selectedProduct.sku} | 
            Toifa: ${selectedProduct.category || '—'} | 
            Zaxira: ${selectedProduct.stock_qty} ${selectedProduct.unit}
        </p>
    `;
    qtyInput.value = 1;
    modal.classList.remove('hidden');
    qtyInput.focus();
    qtyInput.select();
}

function hideModal() {
    document.getElementById('qty-modal').classList.add('hidden');
    selectedProduct = null;
    const qr = document.getElementById('qr-input');
    if (qr) qr.focus();
}

// ════════════════════════════════════════════
// Standard Checkout API Call (ADD TO LIST)
// ════════════════════════════════════════════
async function doStandardCheckout() {
    if (!selectedProduct || !faceVerified) return;

    const quantity = parseInt(document.getElementById('qty-input').value) || 1;
    if (quantity <= 0) return;

    const body = {
        product_id: selectedProduct.id,
        quantity: quantity,
    };

    // Robustly get Target ID - IMMEDIATELY read DOM
    // This ensures we get the latest value even if global state is stale
    const targetSelect = document.getElementById('target-select');
    let finalTargetId = null;

    if (targetSelect && targetSelect.value) {
        finalTargetId = parseInt(targetSelect.value);
    } else if (targetEmployeeId) {
        finalTargetId = targetEmployeeId;
    }

    if (finalTargetId) {
        body.target_employee_id = finalTargetId;
    }

    try {
        const resp = await fetch(CONFIG.urls.checkoutStandard, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.csrfToken
            },
            body: JSON.stringify(body)
        });
        const data = await resp.json();

        if (data.ok) {
            SOUNDS.SUCCESS();
            hideModal();
            currentMovementId = data.movement_id;
            // Update Target UI if inferred
            if (data.target_id) {
                const targetSelect = document.getElementById('target-select');
                if (targetSelect && !targetSelect.value) {
                    targetSelect.value = data.target_id;
                    targetEmployeeId = data.target_id;
                }
                const statusEl = document.getElementById('scan-status');
                if (statusEl) statusEl.innerHTML = `✅ ${data.message} <br><small>Sessiya: <b>${data.target_name}</b></small>`;
            } else {
                document.getElementById('scan-status').innerHTML = `✅ ${data.message}`;
            }

            updateHistoryAndUI(data.items, data.message);
            showToast('success', `✅ ${data.message}`);
        } else {
            SOUNDS.ERROR();
            showToast('error', data.error || 'Xatolik');
            document.getElementById('scan-status').innerHTML = `❌ ${data.error}`;
        }
    } catch (err) {
        SOUNDS.ERROR();
        showToast('error', 'Server xatosi: ' + err.message);
    }
}

// ════════════════════════════════════════════
// Turbo Checkout
// ════════════════════════════════════════════
async function doStandardCheckoutDirect(quantity) {
    if (!selectedProduct || !faceVerified) return;

    const body = {
        product_id: selectedProduct.id,
        quantity: quantity,
    };

    // Robustly get Target ID - IMMEDIATELY read DOM
    const targetSelect = document.getElementById('target-select');
    let finalTargetId = null;

    if (targetSelect && targetSelect.value) {
        finalTargetId = parseInt(targetSelect.value);
    } else if (targetEmployeeId) {
        finalTargetId = targetEmployeeId;
    }

    if (finalTargetId) {
        body.target_employee_id = finalTargetId;
    }

    try {
        const resp = await fetch(CONFIG.urls.checkoutStandard, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.csrfToken
            },
            body: JSON.stringify(body)
        });
        const data = await resp.json();

        if (data.ok) {
            SOUNDS.SUCCESS();
            currentMovementId = data.movement_id;
            // Update Target UI if inferred
            if (data.target_id) {
                const targetSelect = document.getElementById('target-select');
                if (targetSelect && !targetSelect.value) {
                    targetSelect.value = data.target_id;
                    targetEmployeeId = data.target_id;
                }
                const statusEl = document.getElementById('scan-status');
                if (statusEl) statusEl.innerHTML = `⚡ ${data.message} <br><small>Sessiya: <b>${data.target_name}</b></small>`;
            } else {
                document.getElementById('scan-status').innerHTML = `⚡ ${data.message}`;
            }

            updateHistoryAndUI(data.items, data.message);
            showToast('success', `⚡ ${data.message}`);
        } else {
            SOUNDS.ERROR();
            showToast('error', data.error || 'Xatolik');
            document.getElementById('scan-status').innerHTML = `❌ ${data.error}`;
        }
    } catch (err) {
        SOUNDS.ERROR();
        showToast('error', 'Server xatosi: ' + err.message);
    }

    selectedProduct = null;
    const qr = document.getElementById('qr-input');
    if (qr) qr.focus();
}


// ════════════════════════════════════════════
// Emergency Checkout
// ════════════════════════════════════════════
function initEmergencyButton() {
    const btn = document.getElementById('emergency-btn');
    if (!btn) return;

    btn.addEventListener('click', async () => {
        const target = targetEmployeeId
            ? CONFIG.employees.find(e => e.id === targetEmployeeId)?.name || 'boshqa xodim'
            : actor?.name || 'siz';

        if (!confirm(`🚨 DIQQAT!\n\n${target} ga biriktirilgan barcha toifadagi mahsulotlar chiqariladi.\n\nDavom etasizmi?`)) return;

        btn.disabled = true;
        btn.textContent = '⏳ Yuklanmoqda...';

        const body = {};
        if (targetEmployeeId) body.target_employee_id = targetEmployeeId;

        try {
            const resp = await fetch(CONFIG.urls.checkoutEmergency, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CONFIG.csrfToken
                },
                body: JSON.stringify(body)
            });
            const data = await resp.json();

            if (data.ok) {
                SOUNDS.VERIFIED();
                currentMovementId = data.movement_id;
                updateHistoryAndUI(data.items, data.message);
                showToast('success', `🚨 ${data.message}`);
                btn.textContent = '✅ Ro\'yxatga olindi!';
                setTimeout(() => {
                    btn.disabled = false;
                    btn.textContent = '🚨 BARCHA TOIFADAGI MAHSULOTLARNI CHIQARISH';
                }, 2000);
            } else {
                SOUNDS.ERROR();
                showToast('error', data.error || 'Xatolik');
                btn.disabled = false;
                btn.textContent = '🚨 BARCHA TOIFADAGI MAHSULOTLARNI CHIQARISH';
            }
        } catch (err) {
            SOUNDS.ERROR();
            showToast('error', 'Server xatosi: ' + err.message);
            btn.disabled = false;
            btn.textContent = '🚨 BARCHA TOIFADAGI MAHSULOTLARNI CHIQARISH';
        }
    });
}

// ════════════════════════════════════════════
// UI Updates & History
// ════════════════════════════════════════════
function updateHistoryAndUI(items, message) {
    if (!items) return;

    // items from backend is list of all items in movement
    checkoutHistory = items.map(item => ({
        id: item.id,
        name: item.name || item.product__name || '—',
        sku: item.sku || item.product__sku || '—',
        quantity: item.quantity,
    }));

    renderResults(message);
    setStep(3);
}

function renderResults(message) {
    const section = document.getElementById('results-section');
    const tbody = document.getElementById('results-body');
    const badge = document.getElementById('items-count-badge');
    const finalizeBtn = document.getElementById('finalize-btn');
    const cancelBtn = document.getElementById('cancel-btn');

    if (!section || !tbody) return;

    if (checkoutHistory.length > 0) {
        section.classList.add('visible');
        if (finalizeBtn) finalizeBtn.style.display = 'block';
        if (cancelBtn) cancelBtn.style.display = 'block';
    } else {
        // Don't fully hide section, just empty table? Or hide actions?
        // Let's hide actions.
        if (finalizeBtn) finalizeBtn.style.display = 'none';
        if (cancelBtn) cancelBtn.style.display = 'none';
    }

    tbody.innerHTML = checkoutHistory.map((item, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${item.name}</td>
            <td><code>${item.sku}</code></td>
            <td><b>${item.quantity}</b></td>
        </tr>
    `).join('');

    const total = checkoutHistory.reduce((s, i) => s + i.quantity, 0);
    if (badge) badge.textContent = `${total} dona`;

    const summary = document.getElementById('results-summary');
    if (summary && message) {
        summary.innerHTML = `📊 Jami: ${checkoutHistory.length} mahsulot, ${total} dona — ${message}`;
    }
}

// ════════════════════════════════════════════
// Finalize & Cancel Logic
// ════════════════════════════════════════════
function initActionButtons() {
    const finalizeBtn = document.getElementById('finalize-btn');
    const cancelBtn = document.getElementById('cancel-btn');

    if (finalizeBtn) {
        finalizeBtn.addEventListener('click', finalizeCheckout);
    }
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            if (confirm("Rostdan ham barchasini bekor qilasizmi?")) {
                cancelCheckout();
            }
        });
    }
}

function resetUI() {
    console.log("HARD RESET UI TRIGGERED");

    // 1. Reset Data State
    checkoutHistory = [];
    currentMovementId = null;
    actor = null;
    targetEmployeeId = null;
    faceVerified = false;

    // 2. Clear Lists & Counters
    renderResults();
    const countBadge = document.getElementById('items-count-badge');
    if (countBadge) countBadge.textContent = '0 dona';

    // 3. Reset Targets
    const targetSelect = document.getElementById('target-select');
    if (targetSelect) {
        targetSelect.value = "";
        // Optional: clear options if we want to force re-fetch or just keep them?
        // Keep them is fine, but value must be reset.
    }
    const targetCats = document.getElementById('target-categories');
    if (targetCats) targetCats.innerHTML = '';

    document.getElementById('target-section').classList.remove('visible');

    // 4. Reset Face ID UI
    updateFaceUI(false, 'Face tasdiqlanmagan');
    document.getElementById('employee-badge').classList.remove('visible');
    const nameEl = document.getElementById('emp-name');
    if (nameEl) nameEl.innerHTML = '';
    const metaEl = document.getElementById('emp-meta');
    if (metaEl) metaEl.textContent = '';
    const catsEl = document.getElementById('emp-categories');
    if (catsEl) catsEl.innerHTML = '';

    // 5. Hide Action Buttons
    const finalizeBtn = document.getElementById('finalize-btn');
    if (finalizeBtn) finalizeBtn.style.display = 'none';
    const cancelBtn = document.getElementById('cancel-btn');
    if (cancelBtn) cancelBtn.style.display = 'none';

    // 6. Lock Scanner & Reset Steps
    const card = document.getElementById('scanner-card');
    const input = document.getElementById('qr-input');
    const emergBtn = document.getElementById('emergency-btn');

    if (card) card.classList.add('locked');
    if (input) {
        input.disabled = true;
        input.value = '';
    }
    if (emergBtn) emergBtn.disabled = true;

    setStep(1); // Back to Face ID step

    // 7. Explicitly clear face status check interval if any (not used here but good practice)
    // And maybe re-init camera if needed? (Camera stays active)
}

async function finalizeCheckout() {
    if (!currentMovementId) return;

    const finalizeBtn = document.getElementById('finalize-btn');
    finalizeBtn.disabled = true;
    finalizeBtn.textContent = '⏳ Yakunlanmoqda...';

    // Construct URL manually since CONFIG.urls.finalize has check for {id} placeholder
    let url = CONFIG.urls.finalize.replace('{id}', currentMovementId);

    try {
        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': CONFIG.csrfToken
            }
        });
        const data = await resp.json();

        if (data.ok) {
            SOUNDS.VERIFIED();

            // ──────────────────────────────────────────
            // STEP 3: NATIJA (Result)
            // ──────────────────────────────────────────
            setStep(3);

            // Show big success message
            const resultsBody = document.getElementById('results-body');
            if (resultsBody) {
                resultsBody.innerHTML = `
                    <tr>
                        <td colspan="4" style="text-align:center; padding: 40px;">
                            <h2 style="color: #10b981; margin-bottom: 10px;">✅ Yakunlandi</h2>
                            <p style="font-size: 1.2em; color: #334155;">${data.message || 'Muvaffaqiyatli saqlandi'}</p>
                            <p style="color: #64748b;">3 soniyadan so'ng yangilanadi...</p>
                        </td>
                    </tr>
                `;
            }

            // Hide buttons immediately
            document.getElementById('finalize-btn').style.display = 'none';
            document.getElementById('cancel-btn').style.display = 'none';

            // ──────────────────────────────────────────
            // DELAYED FULL RESET (3-5s)
            // ──────────────────────────────────────────
            setTimeout(() => {
                resetUI();
            }, 3000);

        } else {
            SOUNDS.ERROR();
            showToast('error', data.error || 'Xatolik');
        }
    } catch (err) {
        SOUNDS.ERROR();
        showToast('error', 'Server xatosi: ' + err.message);
    } finally {
        if (finalizeBtn) {
            // Only re-enable if NOT successful (if successful, buttons are hidden)
            // But if we are waiting for timeout, button is hidden.
            // If error, we re-enable.
            // The logic: if hidden, don't touch.
            if (finalizeBtn.style.display !== 'none') {
                finalizeBtn.disabled = false;
                finalizeBtn.textContent = '✅ YAKUNLASH';
            }
        }
    }
}

async function cancelCheckout(silent = false) {
    if (!currentMovementId) return;

    let url = CONFIG.urls.cancel.replace('{id}', currentMovementId);
    // Or use discard endpoint? 
    // views.py `cancel_movement` sets status=CANCELLED.

    try {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': CONFIG.csrfToken }
        });

        if (resp.ok) {
            checkoutHistory = [];
            currentMovementId = null;
            renderResults('Bekor qilindi');

            // Hide buttons
            document.getElementById('finalize-btn').style.display = 'none';
            document.getElementById('cancel-btn').style.display = 'none';

            if (!silent) showToast('info', 'Sessiya tozalandi');

            // Reset Target
            const targetSelect = document.getElementById('target-select');
            if (targetSelect) targetSelect.value = "";
            targetEmployeeId = null;
            document.getElementById('target-categories').innerHTML = '';

            document.getElementById('qr-input').focus();
        }
    } catch (err) {
        if (!silent) showToast('error', 'Bekor qilishda xatolik');
    }
}

// ════════════════════════════════════════════
// Settings (Turbo, Sound)
// ════════════════════════════════════════════
function initSettings() {
    const turboCheck = document.getElementById('turbo-mode');
    const soundCheck = document.getElementById('sound-mode');

    if (turboCheck) {
        turboCheck.addEventListener('change', () => {
            turboMode = turboCheck.checked;
            showToast(turboMode ? 'success' : 'error',
                turboMode ? '⚡ Turbo rejim YOQILDI' : '⚡ Turbo rejim O\'CHIRILDI');
        });
    }

    if (soundCheck) {
        soundCheck.addEventListener('change', () => {
            soundEnabled = soundCheck.checked;
        });
    }
}

// ════════════════════════════════════════════
// Toast
// ════════════════════════════════════════════
function showToast(type, message) {
    const id = type === 'success' ? 'toast-success' : 'toast-error';
    const el = document.getElementById(id); // Using existing toast elements
    if (!el) return;

    el.textContent = message;
    el.classList.remove('hidden');

    setTimeout(() => el.classList.add('hidden'), 4000);
}

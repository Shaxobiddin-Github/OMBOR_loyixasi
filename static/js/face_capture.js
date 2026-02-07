// Face Capture and Verification
let video, canvas, ctx;
let faceVerified = false;

document.addEventListener('DOMContentLoaded', () => {
    video = document.getElementById('video');
    canvas = document.getElementById('canvas');

    if (!video || !canvas) return;

    ctx = canvas.getContext('2d');

    // Start webcam
    startCamera();

    // Capture button
    const captureBtn = document.getElementById('capture-btn');
    if (captureBtn) {
        captureBtn.addEventListener('click', captureFace);
    }

    // Check existing face status
    checkFaceStatus();
});

async function startCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: 320,
                height: 240,
                facingMode: 'user'
            }
        });
        video.srcObject = stream;
    } catch (err) {
        console.error('Kamera xatosi:', err);
        updateFaceStatus(false, 'Kamerani ochib bo\'lmadi');
    }
}

async function captureFace() {
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);

    // Send to server for verification
    try {
        const response = await fetch(CONFIG.urls.faceVerify, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.csrfToken
            },
            body: JSON.stringify({ image: dataUrl })
        });

        const data = await response.json();

        if (data.ok) {
            faceVerified = true;
            updateFaceStatus(true, `✅ ${data.name} (${data.confidence})`);
            updateFinalizeButton();
        } else {
            updateFaceStatus(false, data.error || 'Yuz tanilmadi');
        }
    } catch (err) {
        updateFaceStatus(false, 'Server xatosi: ' + err.message);
    }
}

async function checkFaceStatus() {
    try {
        const response = await fetch(CONFIG.urls.faceStatus);
        const data = await response.json();

        if (data.verified) {
            faceVerified = true;
            updateFaceStatus(true, `✅ ${data.name} (${data.confidence})`);
            updateFinalizeButton();
        }
    } catch (err) {
        console.error('Face status check failed:', err);
    }
}

function updateFaceStatus(verified, message) {
    const statusEl = document.getElementById('face-status');
    if (statusEl) {
        statusEl.className = 'face-status' + (verified ? ' verified' : '');
        statusEl.innerHTML = `
            <span class="status-icon">${verified ? '✅' : '❌'}</span>
            <span>${message || (verified ? 'Face tasdiqlangan' : 'Face tasdiqlanmagan')}</span>
        `;
    }
}

function updateFinalizeButton() {
    const btn = document.getElementById('finalize-btn');
    if (btn && faceVerified && typeof movementId !== 'undefined' && movementId && itemsCount > 0) {
        btn.disabled = false;
    }
}

// ============================================================
// 配置
// ============================================================
const API_BASE = '/api';
let accessToken = localStorage.getItem('access_token');
let currentUser = JSON.parse(localStorage.getItem('current_user') || 'null');
let currentStream = null;
let recordsSkip = 0;
const RECORDS_LIMIT = 20;

// 注册/更新照片相关
let capturedImageBase64 = null;
let isFaceDetected = false;

// ============================================================
// DOM 引用
// ============================================================
const $ = id => document.getElementById(id);

// ============================================================
// 初始化
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    // 底部导航切换
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            if ((tab === 'records' || tab === 'profile') && !accessToken) {
                showToast('请先登录', 'info');
                switchTab('login');
                return;
            }
            switchTab(tab);
        });
    });

    // 登录/注册 Tab 切换
    document.querySelectorAll('.auth-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const mode = tab.dataset.auth;
            $('authLogin').style.display = mode === 'login' ? 'block' : 'none';
            $('authRegister').style.display = mode === 'register' ? 'block' : 'none';
        });
    });

    // 登录
    $('loginForm').addEventListener('submit', handleLogin);

    // 注册
    $('registerForm').addEventListener('submit', handleRegister);
    $('regStartCameraBtn').addEventListener('click', () => startCamera('register'));
    $('regCaptureBtn').addEventListener('click', () => capturePhoto('register'));
    $('regRetakeBtn').addEventListener('click', () => retakePhoto('register'));
    $('regAlbumBtn').addEventListener('click', () => $('regFileInput').click());
    $('regFileInput').addEventListener('change', (e) => handleFileSelect(e, 'register'));

    // 签到
    $('signStartCameraBtn').addEventListener('click', startSignCamera);
    $('signCaptureBtn').addEventListener('click', captureSignPhoto);
    $('signModeCamera').addEventListener('click', () => switchSignMode('camera'));
    $('signModeAlbum').addEventListener('click', () => switchSignMode('album'));
    $('signFileInput').addEventListener('change', handleSignFileSelect);
    $('signSubmitBtn').addEventListener('click', submitSign);

    // 记录
    $('recordsRefreshBtn').addEventListener('click', () => loadRecords(true));
    $('recordsLoadMore').addEventListener('click', () => loadRecords(false));

    // 个人中心 - 更新照片
    $('profileStartCameraBtn').addEventListener('click', () => startCamera('profile'));
    $('profileCaptureBtn').addEventListener('click', () => capturePhoto('profile'));
    $('profileRetakeBtn').addEventListener('click', () => retakePhoto('profile'));
    $('profileAlbumBtn').addEventListener('click', () => $('profileFileInput').click());
    $('profileFileInput').addEventListener('change', (e) => handleFileSelect(e, 'profile'));
    $('profileUpdateFaceBtn').addEventListener('click', updateFace);

    // 退出
    $('profileLogoutBtn').addEventListener('click', handleLogout);

    // 初始化UI
    updateUI();
    switchTab('sign');
    if (accessToken) {
        loadRecords(true);
        loadProfileData();
    }
});

// ============================================================
// Tab 切换
// ============================================================
function switchTab(tab) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const pageMap = { sign: 'pageSign', records: 'pageRecords', profile: 'pageProfile', login: 'pageLogin' };
    const target = $(pageMap[tab]);
    if (target) target.classList.add('active');

    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    stopCamera();

    if (tab === 'records' && accessToken) loadRecords(true);
    if (tab === 'profile' && accessToken) loadProfileData();
    if (tab === 'login') {
        // 如果已登录，跳转到个人中心
        if (accessToken) switchTab('profile');
    }
}

// ============================================================
// UI 更新
// ============================================================
function updateUI() {
    const loggedIn = !!accessToken && currentUser;

    // 顶部导航
    $('headerUser').style.display = loggedIn ? 'inline' : 'none';
    $('headerLoginBtn').style.display = loggedIn ? 'none' : 'inline-block';
    $('headerLogoutBtn').style.display = loggedIn ? 'inline-block' : 'none';
    if (loggedIn) $('headerUserName').textContent = currentUser.real_name || '用户';

    // 底部导航 - 根据登录状态显示/隐藏
    const navProfile = document.getElementById('navProfile');
    const navLogin = document.getElementById('navLogin');

    if (loggedIn) {
        // 已登录：显示"我的"，隐藏"登录"
        navProfile.style.display = 'flex';
        navLogin.style.display = 'none';
    } else {
        // 未登录：隐藏"我的"，显示"登录"
        navProfile.style.display = 'none';
        navLogin.style.display = 'flex';
    }

    // 个人中心页面
    $('profileNotLoggedIn').style.display = loggedIn ? 'none' : 'block';
    $('profileLoggedIn').style.display = loggedIn ? 'block' : 'none';

    // 记录页
    $('recordsLoginPrompt').style.display = loggedIn ? 'none' : 'block';
    $('recordsContent').style.display = loggedIn ? 'block' : 'none';

    if (loggedIn) {
        $('profileUserID').textContent = currentUser.user_id || '-';
        $('profileName').textContent = currentUser.real_name || '-';
    }
}

// ============================================================
// 登录
// ============================================================
async function handleLogin(e) {
    e.preventDefault();
    const user_id = $('loginUserID').value.trim();
    const password = $('loginPassword').value.trim();

    if (!user_id || !password) {
        showToast('请填写学号和密码', 'error');
        return;
    }

    showLoading('登录中...');

    try {
        const resp = await fetch(`${API_BASE}/users/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id, password })
        });

        const data = await resp.json();
        if (resp.ok && data.access_token) {
            accessToken = data.access_token;
            currentUser = { user_id: data.user_id, real_name: data.real_name };
            localStorage.setItem('access_token', accessToken);
            localStorage.setItem('current_user', JSON.stringify(currentUser));
            $('loginForm').reset();
            updateUI();
            showToast(`欢迎回来，${data.real_name}！`, 'success');
            loadRecords(true);
            loadProfileData();
            switchTab('sign');
        } else {
            showToast(data.detail || '登录失败', 'error');
        }
    } catch (err) {
        showToast('登录请求失败: ' + err.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================================
// 退出
// ============================================================
function handleLogout() {
    accessToken = null;
    currentUser = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_user');
    stopCamera();
    updateUI();
    showToast('已退出登录');
    switchTab('sign');
}

// ============================================================
// 注册
// ============================================================
async function handleRegister(e) {
    e.preventDefault();

    const user_id = $('regUserID').value.trim();
    const real_name = $('regRealName').value.trim();
    const password = $('regPassword').value;
    const confirm = $('regConfirmPassword').value;

    if (!user_id || !real_name || !password) {
        showToast('请填写所有信息', 'error');
        return;
    }
    if (password !== confirm) {
        showToast('两次密码不一致', 'error');
        return;
    }
    if (!capturedImageBase64 || !isFaceDetected) {
        showToast('请先拍照并通过人脸检测', 'error');
        return;
    }

    showLoading('注册中...');

    try {
        const resp = await fetch(`${API_BASE}/users/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id,
                password,
                real_name,
                face_image_base64: capturedImageBase64
            })
        });

        const data = await resp.json();
        if (resp.ok) {
            showToast('注册成功！请登录', 'success');
            $('registerForm').reset();
            resetPhotoCapture('register');
            // 切换到登录
            document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
            document.querySelector('.auth-tab[data-auth="login"]').classList.add('active');
            $('authLogin').style.display = 'block';
            $('authRegister').style.display = 'none';
            $('loginUserID').value = user_id;
        } else {
            showToast(data.detail || '注册失败', 'error');
        }
    } catch (err) {
        showToast('注册请求失败: ' + err.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================================
// 摄像头通用
// ============================================================
async function startCamera(type) {
    try {
        stopCamera();
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }
        });
        currentStream = stream;

        let videoId, captureBtnId, startBtnId;
        if (type === 'register') {
            videoId = 'regVideo';
            captureBtnId = 'regCaptureBtn';
            startBtnId = 'regStartCameraBtn';
        } else if (type === 'profile') {
            videoId = 'profileVideo';
            captureBtnId = 'profileCaptureBtn';
            startBtnId = 'profileStartCameraBtn';
        } else {
            return;
        }

        const video = $(videoId);
        video.srcObject = stream;
        await video.play();
        $(captureBtnId).disabled = false;
        $(startBtnId).textContent = '📷 已开启';
        showToast('摄像头已开启');
    } catch (err) {
        showToast('无法访问摄像头: ' + err.message, 'error');
    }
}

function stopCamera() {
    if (currentStream) {
        currentStream.getTracks().forEach(t => t.stop());
        currentStream = null;
    }
    ['regVideo', 'profileVideo', 'signVideo'].forEach(id => {
        const v = document.getElementById(id);
        if (v) v.srcObject = null;
    });
}

// ============================================================
// 拍照通用
// ============================================================
function capturePhoto(type) {
    let videoId, canvasId, previewId, statusId, retakeBtnId, submitBtnId, startBtnId, captureBtnId;
    let isRegister = false;

    if (type === 'register') {
        videoId = 'regVideo';
        canvasId = 'regCanvas';
        previewId = 'regPhotoPreview';
        statusId = 'regDetectStatus';
        retakeBtnId = 'regRetakeBtn';
        submitBtnId = 'regSubmitBtn';
        startBtnId = 'regStartCameraBtn';
        captureBtnId = 'regCaptureBtn';
        isRegister = true;
    } else if (type === 'profile') {
        videoId = 'profileVideo';
        canvasId = 'profileCanvas';
        previewId = 'profilePhotoPreview';
        statusId = 'profileDetectStatus';
        retakeBtnId = 'profileRetakeBtn';
        submitBtnId = 'profileUpdateFaceBtn';
        startBtnId = 'profileStartCameraBtn';
        captureBtnId = 'profileCaptureBtn';
        isRegister = false;
    } else {
        return;
    }

    const video = $(videoId);
    if (!video.srcObject) {
        showToast('请先开启摄像头', 'error');
        return;
    }

    const canvas = $(canvasId);
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    const base64 = dataUrl.split(',')[1];

    // 显示预览
    const preview = $(previewId);
    preview.style.display = 'block';
    $(previewId + 'Img').src = dataUrl;
    const status = $(statusId);
    status.className = 'preview-status loading';
    status.textContent = '⏳ 检测人脸...';

    // 隐藏摄像头
    $(videoId).parentElement.style.display = 'none';
    $(captureBtnId).disabled = true;
    $(startBtnId).textContent = '📷 重新开启';

    // 检测人脸
    detectFace(base64, type);
}

function handleFileSelect(e, type) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(ev) {
        const base64 = ev.target.result.split(',')[1];
        // 显示预览
        let previewId, statusId;
        if (type === 'register') {
            previewId = 'regPhotoPreview';
            statusId = 'regDetectStatus';
        } else if (type === 'profile') {
            previewId = 'profilePhotoPreview';
            statusId = 'profileDetectStatus';
        }
        const preview = $(previewId);
        preview.style.display = 'block';
        $(previewId + 'Img').src = ev.target.result;
        const status = $(statusId);
        status.className = 'preview-status loading';
        status.textContent = '⏳ 检测人脸...';
        detectFace(base64, type);
    };
    reader.readAsDataURL(file);
}

async function detectFace(base64Data, type) {
    capturedImageBase64 = base64Data;
    isFaceDetected = false;

    try {
        const resp = await fetch(`${API_BASE}/attendance/detect-face`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_base64: base64Data })
        });

        const data = await resp.json();
        let statusId, submitBtnId, retakeBtnId;

        if (type === 'register') {
            statusId = 'regDetectStatus';
            submitBtnId = 'regSubmitBtn';
            retakeBtnId = 'regRetakeBtn';
        } else if (type === 'profile') {
            statusId = 'profileDetectStatus';
            submitBtnId = 'profileUpdateFaceBtn';
            retakeBtnId = 'profileRetakeBtn';
        }

        const status = $(statusId);

        if (resp.ok && data.success && data.has_face) {
            isFaceDetected = true;
            status.className = 'preview-status success';
            status.textContent = `✅ 检测到人脸 (${data.face_count}张)`;
            $(submitBtnId).disabled = false;
            showToast('人脸检测通过！', 'success');
        } else {
            status.className = 'preview-status error';
            status.textContent = '❌ 未检测到人脸，请重新拍摄';
            $(submitBtnId).disabled = true;
            showToast('未检测到人脸，请重新拍摄', 'error');
        }

        $(retakeBtnId).style.display = 'inline-block';

    } catch (err) {
        const statusId = type === 'register' ? 'regDetectStatus' : 'profileDetectStatus';
        $(statusId).className = 'preview-status error';
        $(statusId).textContent = '⚠️ 检测失败: ' + err.message;
        showToast('检测失败: ' + err.message, 'error');
    }
}

function retakePhoto(type) {
    capturedImageBase64 = null;
    isFaceDetected = false;

    let videoId, previewId, retakeBtnId, submitBtnId, captureBtnId, startBtnId;
    if (type === 'register') {
        videoId = 'regVideo';
        previewId = 'regPhotoPreview';
        retakeBtnId = 'regRetakeBtn';
        submitBtnId = 'regSubmitBtn';
        captureBtnId = 'regCaptureBtn';
        startBtnId = 'regStartCameraBtn';
    } else if (type === 'profile') {
        videoId = 'profileVideo';
        previewId = 'profilePhotoPreview';
        retakeBtnId = 'profileRetakeBtn';
        submitBtnId = 'profileUpdateFaceBtn';
        captureBtnId = 'profileCaptureBtn';
        startBtnId = 'profileStartCameraBtn';
    }

    $(previewId).style.display = 'none';
    $(videoId).parentElement.style.display = 'block';
    $(retakeBtnId).style.display = 'none';
    $(submitBtnId).disabled = true;
    $(captureBtnId).disabled = false;
    $(startBtnId).textContent = '📷 开启摄像头';
    startCamera(type);
}

function resetPhotoCapture(type) {
    capturedImageBase64 = null;
    isFaceDetected = false;
    let previewId, retakeBtnId, submitBtnId, videoId;
    if (type === 'register') {
        previewId = 'regPhotoPreview';
        retakeBtnId = 'regRetakeBtn';
        submitBtnId = 'regSubmitBtn';
        videoId = 'regVideo';
    } else if (type === 'profile') {
        previewId = 'profilePhotoPreview';
        retakeBtnId = 'profileRetakeBtn';
        submitBtnId = 'profileUpdateFaceBtn';
        videoId = 'profileVideo';
    }
    $(previewId).style.display = 'none';
    $(retakeBtnId).style.display = 'none';
    $(submitBtnId).disabled = true;
    $(videoId).parentElement.style.display = 'block';
    stopCamera();
}

// ============================================================
// 更新人脸照片
// ============================================================
async function updateFace() {
    if (!accessToken) {
        showToast('请先登录', 'error');
        return;
    }
    if (!capturedImageBase64 || !isFaceDetected) {
        showToast('请先拍照并通过人脸检测', 'error');
        return;
    }

    showLoading('更新中...');

    try {
        const resp = await fetch(`${API_BASE}/users/update-face`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ face_image_base64: capturedImageBase64 })
        });

        const data = await resp.json();
        if (resp.ok) {
            showToast('人脸照片更新成功！', 'success');
            resetPhotoCapture('profile');
            loadProfileData();
        } else {
            showToast(data.detail || '更新失败', 'error');
        }
    } catch (err) {
        showToast('更新请求失败: ' + err.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================================
// 签到（不需要登录）
// ============================================================
function switchSignMode(mode) {
    const cameraArea = $('signCameraArea');
    const albumArea = $('signAlbumArea');
    const cameraBtn = $('signModeCamera');
    const albumBtn = $('signModeAlbum');

    if (mode === 'camera') {
        cameraArea.style.display = 'block';
        albumArea.style.display = 'none';
        cameraBtn.classList.add('active');
        albumBtn.classList.remove('active');
        stopCamera();
    } else {
        cameraArea.style.display = 'none';
        albumArea.style.display = 'block';
        cameraBtn.classList.remove('active');
        albumBtn.classList.add('active');
        stopCamera();
    }
    $('signResult').style.display = 'none';
}

async function startSignCamera() {
    try {
        stopCamera();
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }
        });
        currentStream = stream;
        const video = $('signVideo');
        video.srcObject = stream;
        await video.play();
        $('signCaptureBtn').disabled = false;
        $('signStartCameraBtn').textContent = '📷 已开启';
        showToast('摄像头已开启');
    } catch (err) {
        showToast('无法访问摄像头: ' + err.message, 'error');
    }
}

async function captureSignPhoto() {
    const video = $('signVideo');
    if (!video.srcObject) {
        showToast('请先开启摄像头', 'error');
        return;
    }

    const canvas = $('signCanvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    const base64 = dataUrl.split(',')[1];

    await doSign(base64);
}

function handleSignFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(ev) {
        const img = $('signPreviewImg');
        img.src = ev.target.result;
        img.style.display = 'block';
        $('signUploadArea').querySelector('.upload-placeholder').style.display = 'none';
        $('signSubmitBtn').disabled = false;
    };
    reader.readAsDataURL(file);
}

async function submitSign() {
    const file = $('signFileInput').files[0];
    if (!file) {
        showToast('请选择照片', 'error');
        return;
    }

    try {
        const base64 = await fileToBase64(file);
        await doSign(base64.split(',')[1]);
    } catch (err) {
        showToast('读取照片失败: ' + err.message, 'error');
    }
}

// ============================================================
// 签到核心逻辑（每次签到都写入数据库）
// ============================================================
async function doSign(base64Data) {
    showLoading('签到中...');

    try {
        const resp = await fetch(`${API_BASE}/attendance/sign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_base64: base64Data })
        });

        const data = await resp.json();
        const resultDiv = $('signResult');
        resultDiv.style.display = 'block';

        if (resp.ok && data.success) {
            // 格式化签到时间
            const signTime = new Date(data.sign_time);
            const timeStr = signTime.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });

            // 显示签到结果 - 格式: "学号 用户名 已在 时间 签到"
            resultDiv.className = 'sign-result success';
            resultDiv.innerHTML = `
                <span class="result-icon">✅</span>
                <strong>签到成功</strong>
                <div class="result-detail">
                    📋 ${data.user_id} ${data.user_name}<br>
                    🕐 已在 ${timeStr} 签到<br>
                    📊 今日第 ${data.today_count} 次签到
                </div>
            `;

            // Toast 提示
            const toastMsg = `${data.user_id} ${data.user_name} 已在 ${signTime.toLocaleTimeString('zh-CN')} 签到`;
            showToast(toastMsg, 'success');

            // 刷新记录
            if (accessToken) {
                loadRecords(true);
                loadProfileData();
            }

            // 重置
            $('signFileInput').value = '';
            $('signPreviewImg').style.display = 'none';
            $('signUploadArea').querySelector('.upload-placeholder').style.display = 'block';
            $('signSubmitBtn').disabled = true;
            stopCamera();
        } else {
            resultDiv.className = 'sign-result error';
            resultDiv.innerHTML = `
                <span class="result-icon">❌</span>
                <strong>签到失败</strong>
                <div class="result-detail">${data.detail || '请确保照片清晰且包含完整人脸'}</div>
            `;
            showToast(data.detail || '签到失败', 'error');
        }
    } catch (err) {
        showToast('签到请求失败: ' + err.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================================
// 签到记录（需要登录）
// ============================================================
async function loadRecords(reset = true) {
    if (!accessToken) return;

    if (reset) {
        recordsSkip = 0;
        $('recordsList').innerHTML = '';
        $('recordsLoadMore').style.display = 'none';
    }

    try {
        const url = `${API_BASE}/attendance/my-records?skip=${recordsSkip}&limit=${RECORDS_LIMIT}`;
        console.log('📡 请求记录 URL:', url);

        const resp = await fetch(url, {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });

        console.log('📡 响应状态:', resp.status);

        if (resp.status === 401) {
            handleLogout();
            return;
        }

        if (!resp.ok) {
            const errorData = await resp.json().catch(() => ({}));
            showToast(errorData.detail || '加载记录失败', 'error');
            return;
        }

        const data = await resp.json();
        console.log('📡 返回数据:', data);

        if (!data || typeof data !== 'object') {
            console.error('❌ 数据格式错误:', data);
            showToast('加载记录失败：数据格式错误', 'error');
            return;
        }

        const records = Array.isArray(data.records) ? data.records : [];
        const total = typeof data.total === 'number' ? data.total : 0;

        console.log(`📋 记录数: ${records.length}, 总数: ${total}`);

        $('recordsCount').textContent = `共 ${total} 条`;

        if (total === 0 || records.length === 0) {
            $('recordsList').innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📭</span>
                    <p>还没有签到记录，去签到吧！</p>
                </div>
            `;
            $('recordsLoadMore').style.display = 'none';
            return;
        }

        if (reset) $('recordsList').innerHTML = '';

        records.forEach(r => {
            const div = document.createElement('div');
            div.className = 'record-item';
            const d = new Date(r.sign_time);
            div.innerHTML = `
                <div class="record-left">
                    <span class="record-date">${d.toLocaleDateString()}</span>
                    <span class="record-time">${d.toLocaleTimeString()}</span>
                </div>
                <div class="record-right">
                    <span style="font-size:12px;color:#4a6cf7;">✅ 已签到</span>
                </div>
            `;
            $('recordsList').appendChild(div);
        });

        if (records.length === RECORDS_LIMIT && recordsSkip + RECORDS_LIMIT < total) {
            $('recordsLoadMore').style.display = 'block';
            recordsSkip += RECORDS_LIMIT;
        } else {
            $('recordsLoadMore').style.display = 'none';
        }

    } catch (err) {
        console.error('❌ 加载记录失败:', err);
        showToast('加载记录失败: ' + err.message, 'error');
    }
}

function loadMoreRecords() {
    loadRecords(false);
}

// ============================================================
// 个人中心数据
// ============================================================
async function loadProfileData() {
    if (!accessToken) return;

    try {
        // 今日签到状态
        const resp1 = await fetch(`${API_BASE}/attendance/today-status`, {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        if (resp1.ok) {
            const data = await resp1.json();
            if (data && data.has_signed !== undefined) {
                if (data.has_signed) {
                    const count = data.today_count || 1;
                    const time = data.sign_time ? new Date(data.sign_time).toLocaleTimeString() : '';
                    $('profileTodayStatus').textContent = `✅ 已签到 ${count} 次 (最近 ${time})`;
                    $('profileTodayStatus').style.color = '#2e7d32';
                } else {
                    $('profileTodayStatus').textContent = '❌ 未签到';
                    $('profileTodayStatus').style.color = '#c62828';
                }
            }
        }

        // 总签到数
        const resp2 = await fetch(`${API_BASE}/attendance/my-records?limit=1`, {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        if (resp2.ok) {
            const data = await resp2.json();
            if (data && data.total !== undefined) {
                $('profileTotalSigns').textContent = `${data.total || 0} 次`;
            }
        }

        // 是否有照片
        const resp3 = await fetch(`${API_BASE}/users/has-face`, {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        if (resp3.ok) {
            const data = await resp3.json();
            if (data && data.has_face !== undefined) {
                $('profileHasFace').textContent = data.has_face ? '✅ 已上传' : '❌ 未上传';
                $('profileHasFace').style.color = data.has_face ? '#2e7d32' : '#c62828';
            }
        }

    } catch (err) {
        console.error('加载个人数据失败', err);
    }
}

// ============================================================
// 工具函数
// ============================================================
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

function showToast(msg, type = 'info') {
    const icons = { success: '✅ ', error: '❌ ', info: 'ℹ️ ' };
    alert((icons[type] || 'ℹ️ ') + msg);
}

function showLoading(text = '处理中...') {
    $('loadingOverlay').style.display = 'flex';
    $('loadingText').textContent = text;
}

function hideLoading() {
    $('loadingOverlay').style.display = 'none';
}

// 点击弹窗外关闭
document.querySelector('.modal')?.addEventListener('click', function(e) {
    if (e.target === this) this.style.display = 'none';
});
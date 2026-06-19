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

// 摄像头是否已开启
let isCameraReady = false;

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
    $('regCaptureBtn').addEventListener('click', () => handleCapture('register'));

    // 签到
    $('signCaptureBtn').addEventListener('click', handleSignCapture);
    $('signRetakeBtn').addEventListener('click', () => retakeSignPhoto());

    // 记录
    $('recordsRefreshBtn').addEventListener('click', () => loadRecords(true));
    $('recordsLoadMore').addEventListener('click', () => loadRecords(false));

    // 个人中心 - 更新照片
    $('profileCaptureBtn').addEventListener('click', () => handleCapture('profile'));
    $('profileRetakeBtn').addEventListener('click', () => retakePhoto('profile'));
    $('profileUpdateFaceBtn').addEventListener('click', updateFace);

    // 退出
    $('profileLogoutBtn').addEventListener('click', handleLogout);

    // 初始化UI
    updateUI();
    switchTab('sign');
    if (accessToken) {
        console.log('🔑 检测到已登录 Token:', accessToken);
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

    if (tab === 'records' && accessToken) {
        console.log('📋 切换到记录页，加载数据...');
        loadRecords(true);
    }
    if (tab === 'profile' && accessToken) loadProfileData();
    if (tab === 'login') {
        if (accessToken) switchTab('profile');
    }
}

// ============================================================
// UI 更新
// ============================================================
function updateUI() {
    const loggedIn = !!accessToken && currentUser;
    console.log('🔄 更新 UI, loggedIn:', loggedIn);

    $('headerUser').style.display = loggedIn ? 'inline' : 'none';
    $('headerLoginBtn').style.display = loggedIn ? 'none' : 'inline-block';
    $('headerLogoutBtn').style.display = loggedIn ? 'inline-block' : 'none';
    if (loggedIn) $('headerUserName').textContent = currentUser.real_name || '用户';

    const navProfile = document.getElementById('navProfile');
    const navLogin = document.getElementById('navLogin');

    if (loggedIn) {
        navProfile.style.display = 'flex';
        navLogin.style.display = 'none';
    } else {
        navProfile.style.display = 'none';
        navLogin.style.display = 'flex';
    }

    $('profileNotLoggedIn').style.display = loggedIn ? 'none' : 'block';
    $('profileLoggedIn').style.display = loggedIn ? 'block' : 'none';
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
        console.log('📡 登录响应:', data);

        if (resp.ok && data.access_token) {
            accessToken = data.access_token;
            currentUser = { user_id: data.user_id, real_name: data.real_name };
            localStorage.setItem('access_token', accessToken);
            localStorage.setItem('current_user', JSON.stringify(currentUser));
            $('loginForm').reset();
            updateUI();
            showToast(`欢迎回来，${data.real_name}！`, 'success');
            console.log('✅ 登录成功，准备加载记录...');
            // 延迟一下确保 UI 更新完成
            setTimeout(() => {
                loadRecords(true);
                loadProfileData();
            }, 100);
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
// 摄像头管理（只负责开启，不弹窗）
// ============================================================
async function ensureCamera(type) {
    try {
        // 如果已经开启，直接返回
        if (isCameraReady && currentStream) {
            return true;
        }

        // 停止之前的摄像头
        stopCamera();

        let videoId;
        if (type === 'register') {
            videoId = 'regVideo';
        } else if (type === 'profile') {
            videoId = 'profileVideo';
        } else if (type === 'sign') {
            videoId = 'signVideo';
        } else {
            return false;
        }

        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }
        });
        currentStream = stream;

        const video = $(videoId);
        video.srcObject = stream;
        await video.play();

        // 显示摄像头，隐藏预览
        const videoWrapper = video.parentElement;
        if (videoWrapper) {
            videoWrapper.style.display = 'block';
        }
        if (type === 'register') {
            $('regPhotoPreview').style.display = 'none';
        } else if (type === 'profile') {
            $('profilePhotoPreview').style.display = 'none';
        } else if (type === 'sign') {
            $('signPhotoPreview').style.display = 'none';
            $('signResult').style.display = 'none';
        }

        isCameraReady = true;
        return true;
    } catch (err) {
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            showToast('您拒绝了摄像头权限，请在浏览器设置中允许', 'error');
        } else {
            showToast('无法访问摄像头: ' + err.message, 'error');
        }
        return false;
    }
}

function stopCamera() {
    if (currentStream) {
        currentStream.getTracks().forEach(t => t.stop());
        currentStream = null;
    }
    isCameraReady = false;
    ['regVideo', 'profileVideo', 'signVideo'].forEach(id => {
        const v = document.getElementById(id);
        if (v) v.srcObject = null;
    });
}

// ============================================================
// 拍照处理（通用）
// ============================================================
async function handleCapture(type) {
    // 检查摄像头是否已开启
    if (!isCameraReady || !currentStream) {
        // 摄像头未开启 → 弹窗确认开启摄像头
        const confirmOpen = confirm('📷 是否开启摄像头？');
        if (!confirmOpen) {
            showToast('已取消', 'info');
            return;
        }

        // 开启摄像头（不拍照）
        const ready = await ensureCamera(type);
        if (!ready) {
            return;
        }
        showToast('摄像头已开启，请再次点击拍照', 'success');
        return;
    }

    // 摄像头已开启 → 直接拍照
    await takePhoto(type);
}

// ============================================================
// 执行拍照
// ============================================================
async function takePhoto(type) {
    let videoId, canvasId, previewId, statusId, retakeBtnId, submitBtnId, captureBtnId;

    if (type === 'register') {
        videoId = 'regVideo';
        canvasId = 'regCanvas';
        previewId = 'regPhotoPreview';
        statusId = 'regDetectStatus';
        retakeBtnId = 'regRetakeBtn';
        submitBtnId = 'regSubmitBtn';
        captureBtnId = 'regCaptureBtn';
    } else if (type === 'profile') {
        videoId = 'profileVideo';
        canvasId = 'profileCanvas';
        previewId = 'profilePhotoPreview';
        statusId = 'profileDetectStatus';
        retakeBtnId = 'profileRetakeBtn';
        submitBtnId = 'profileUpdateFaceBtn';
        captureBtnId = 'profileCaptureBtn';
    } else {
        return;
    }

    const video = $(videoId);
    if (!video || !video.srcObject) {
        showToast('摄像头未就绪，请重试', 'error');
        return;
    }

    // 拍照
    const canvas = $(canvasId);
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    const base64 = dataUrl.split(',')[1];

    // 显示预览
    const videoWrapper = video.parentElement;
    if (videoWrapper) {
        videoWrapper.style.display = 'none';
    }

    const preview = $(previewId);
    if (preview) {
        preview.style.display = 'block';
        const previewImg = preview.querySelector('img');
        if (previewImg) {
            previewImg.src = dataUrl;
        }
    }

    const status = $(statusId);
    if (status) {
        status.className = 'preview-status loading';
        status.textContent = '⏳ 检测人脸...';
    }

    $(captureBtnId).disabled = true;
    $(retakeBtnId).style.display = 'inline-block';
    $(submitBtnId).disabled = true;

    // 检测人脸
    await detectFace(base64, type);
}

// ============================================================
// 人脸检测
// ============================================================
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
        } else {
            return;
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

// ============================================================
// 重新拍摄（通用）
// ============================================================
function retakePhoto(type) {
    capturedImageBase64 = null;
    isFaceDetected = false;

    let videoId, previewId, retakeBtnId, submitBtnId, captureBtnId;
    if (type === 'register') {
        videoId = 'regVideo';
        previewId = 'regPhotoPreview';
        retakeBtnId = 'regRetakeBtn';
        submitBtnId = 'regSubmitBtn';
        captureBtnId = 'regCaptureBtn';
    } else if (type === 'profile') {
        videoId = 'profileVideo';
        previewId = 'profilePhotoPreview';
        retakeBtnId = 'profileRetakeBtn';
        submitBtnId = 'profileUpdateFaceBtn';
        captureBtnId = 'profileCaptureBtn';
    } else {
        return;
    }

    $(previewId).style.display = 'none';
    const videoWrapper = $(videoId)?.parentElement;
    if (videoWrapper) {
        videoWrapper.style.display = 'block';
    }
    $(retakeBtnId).style.display = 'none';
    $(submitBtnId).disabled = true;
    $(captureBtnId).disabled = false;

    // 重新开启摄像头
    isCameraReady = false;
    ensureCamera(type);
}

function resetPhotoCapture(type) {
    capturedImageBase64 = null;
    isFaceDetected = false;
    let previewId, retakeBtnId, submitBtnId, videoId, captureBtnId;
    if (type === 'register') {
        previewId = 'regPhotoPreview';
        retakeBtnId = 'regRetakeBtn';
        submitBtnId = 'regSubmitBtn';
        videoId = 'regVideo';
        captureBtnId = 'regCaptureBtn';
    } else if (type === 'profile') {
        previewId = 'profilePhotoPreview';
        retakeBtnId = 'profileRetakeBtn';
        submitBtnId = 'profileUpdateFaceBtn';
        videoId = 'profileVideo';
        captureBtnId = 'profileCaptureBtn';
    } else {
        return;
    }
    $(previewId).style.display = 'none';
    $(retakeBtnId).style.display = 'none';
    $(submitBtnId).disabled = true;
    $(captureBtnId).disabled = false;
    const videoWrapper = $(videoId)?.parentElement;
    if (videoWrapper) {
        videoWrapper.style.display = 'block';
    }
    isCameraReady = false;
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
async function handleSignCapture() {
    // 检查摄像头是否已开启
    if (!isCameraReady || !currentStream) {
        // 摄像头未开启 → 弹窗确认开启摄像头
        const confirmOpen = confirm('📷 是否开启摄像头？');
        if (!confirmOpen) {
            showToast('已取消', 'info');
            return;
        }

        // 开启摄像头（不拍照）
        const ready = await ensureCamera('sign');
        if (!ready) {
            return;
        }
        showToast('摄像头已开启，请再次点击拍照', 'success');
        return;
    }

    // 摄像头已开启 → 直接拍照
    await takeSignPhoto();
}

// ============================================================
// 执行签到拍照
// ============================================================
async function takeSignPhoto() {
    const video = $('signVideo');
    if (!video || !video.srcObject) {
        showToast('摄像头未就绪，请重试', 'error');
        return;
    }

    const canvas = $('signCanvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    const base64 = dataUrl.split(',')[1];

    // 显示预览
    const videoWrapper = video.parentElement;
    if (videoWrapper) {
        videoWrapper.style.display = 'none';
    }
    const preview = $('signPhotoPreview');
    if (preview) {
        preview.style.display = 'block';
        const previewImg = preview.querySelector('img');
        if (previewImg) {
            previewImg.src = dataUrl;
        }
    }

    $('signRetakeBtn').style.display = 'inline-block';
    $('signCaptureBtn').disabled = true;

    // 执行签到
    await doSign(base64);
}

function retakeSignPhoto() {
    capturedImageBase64 = null;
    isFaceDetected = false;

    $('signPhotoPreview').style.display = 'none';
    $('signResult').style.display = 'none';
    const videoWrapper = $('signVideo')?.parentElement;
    if (videoWrapper) {
        videoWrapper.style.display = 'block';
    }
    $('signRetakeBtn').style.display = 'none';
    $('signCaptureBtn').disabled = false;

    isCameraReady = false;
    ensureCamera('sign');
}

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
            const signTime = new Date(data.sign_time);
            const timeStr = signTime.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });

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

            const toastMsg = `${data.user_id} ${data.user_name} 已在 ${signTime.toLocaleTimeString('zh-CN')} 签到`;
            showToast(toastMsg, 'success');

            if (accessToken) {
                loadRecords(true);
                loadProfileData();
            }

            $('signCaptureBtn').disabled = false;
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

async function loadRecords(reset = true) {
    if (!accessToken) {
        console.warn('⚠️ 未登录，无法加载记录');
        return;
    }

    if (reset) {
        recordsSkip = 0;
        $('recordsList').innerHTML = '';
        $('recordsLoadMore').style.display = 'none';
    }

    try {
        const url = `${API_BASE}/attendance/my-records?skip=${recordsSkip}&limit=${RECORDS_LIMIT}`;
        console.log('📡 请求记录 URL:', url);
        console.log('📡 Token:', accessToken);

        const resp = await fetch(url, {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });

        console.log('📡 响应状态:', resp.status);
        console.log('📡 响应头:', resp.headers);

        // 先获取响应文本
        const responseText = await resp.text();
        console.log('📡 原始响应:', responseText);

        if (resp.status === 401) {
            console.warn('⚠️ Token 已过期，自动退出');
            handleLogout();
            return;
        }

        // 尝试解析 JSON
        let data;
        try {
            data = JSON.parse(responseText);
        } catch (parseError) {
            console.error('❌ JSON 解析失败:', parseError);
            console.error('❌ 原始响应:', responseText);
            showToast('服务器返回数据格式错误，请联系管理员', 'error');
            return;
        }

        console.log('📡 解析后的数据:', data);

        if (!data || typeof data !== 'object') {
            console.error('❌ 数据格式错误:', data);
            showToast('加载记录失败：数据格式错误', 'error');
            return;
        }

        const records = Array.isArray(data.records) ? data.records : [];
        const total = typeof data.total === 'number' ? data.total : 0;

        console.log(`📋 记录数: ${records.length}, 总数: ${total}`);

        // 更新显示
        $('recordsCount').textContent = `共 ${total} 条`;

        if (total === 0 || records.length === 0) {
            console.log('📭 没有记录');
            $('recordsList').innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📭</span>
                    <p>还没有签到记录，去签到吧！</p>
                </div>
            `;
            $('recordsLoadMore').style.display = 'none';
            return;
        }

        if (reset) {
            $('recordsList').innerHTML = '';
            console.log('🔄 重置列表');
        }

        records.forEach((r, index) => {
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
            console.log(`  ✅ 添加记录 ${index + 1}: ${d.toLocaleString()}`);
        });

        // 处理加载更多
        if (records.length === RECORDS_LIMIT && recordsSkip + RECORDS_LIMIT < total) {
            $('recordsLoadMore').style.display = 'block';
            recordsSkip += RECORDS_LIMIT;
            console.log(`📌 加载更多，当前 skip=${recordsSkip}`);
        } else {
            $('recordsLoadMore').style.display = 'none';
            console.log('📌 没有更多记录');
        }

    } catch (err) {
        console.error('❌ 加载记录失败:', err);
        showToast('加载记录失败: ' + err.message, 'error');
    }
}

// ============================================================
// 个人中心数据
// ============================================================
async function loadProfileData() {
    if (!accessToken) {
        console.warn('⚠️ 未登录，无法加载个人数据');
        return;
    }

    try {
        console.log('📡 开始加载个人中心数据...');

        // ========== 1. 获取用户信息（包含 updated_at）==========
        const resp0 = await fetch(`${API_BASE}/users/me`, {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        console.log('📡 /api/users/me 响应状态:', resp0.status);

        if (resp0.ok) {
            const userData = await resp0.json();
            console.log('📡 [users/me] 完整响应:', JSON.stringify(userData, null, 2));

            // 更新基本信息
            if (userData.user_id) {
                $('profileUserID').textContent = userData.user_id;
            }
            if (userData.real_name) {
                $('profileName').textContent = userData.real_name;
            }

            // 更新 updated_at
            if (userData.updated_at) {
                const updateTime = new Date(userData.updated_at);
                const timeStr = updateTime.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    hour12: false
                });
                console.log('📡 格式化后的更新时间:', timeStr);
                $('profileLastUpdate').textContent = timeStr;
            } else {
                console.warn('⚠️ updated_at 为空');
                $('profileLastUpdate').textContent = '暂无';
            }
        } else {
            console.error('❌ 获取用户信息失败:', resp0.status);
        }

        // ========== 2. 获取今日签到状态 ==========
        const resp1 = await fetch(`${API_BASE}/attendance/today-status`, {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        if (resp1.ok) {
            const data = await resp1.json();
            console.log('📡 [today-status] 响应:', data);
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

        // ========== 3. 获取总签到次数 ==========
        const resp2 = await fetch(`${API_BASE}/attendance/my-records?limit=1`, {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        if (resp2.ok) {
            const data = await resp2.json();
            if (data && data.total !== undefined) {
                $('profileTotalSigns').textContent = `${data.total || 0} 次`;
            }
        }

        // ========== 4. 检查是否有人脸 ==========
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

        console.log('✅ 个人中心数据加载完成');

    } catch (err) {
        console.error('❌ 加载个人数据失败:', err);
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
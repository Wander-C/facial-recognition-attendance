// API 配置
const API_BASE_URL = '/api';
let accessToken = null;
let currentUser = null;
let currentStream = null;

// 注册流程变量
let capturedImageBase64 = null;      // 拍照后的图片（未检测）
let detectedFaceBase64 = null;       // 通过人脸检测的图片
let isFaceDetected = false;           // 是否通过人脸检测

// DOM 元素
const loginPage = document.getElementById('loginPage');
const registerPage = document.getElementById('registerPage');
const signinPage = document.getElementById('signinPage');
const navLinks = document.getElementById('navLinks');
const userInfo = document.getElementById('userInfo');
const userNameSpan = document.getElementById('userName');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    checkLoginStatus();

    // 绑定导航事件
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = btn.dataset.page;
            if (page === 'login') {
                showLoginPage();
            } else if (page === 'register') {
                showRegisterPage();
            }
        });
    });

    // 绑定表单事件
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('registerForm').addEventListener('submit', handleRegister);

    // 注册页面切换按钮
    document.getElementById('goToRegisterBtn').addEventListener('click', showRegisterPage);
    document.getElementById('goToLoginBtn').addEventListener('click', showLoginPage);

    // 注册页面摄像头
    document.getElementById('startCameraBtn').addEventListener('click', () => startCamera('register'));
    document.getElementById('capturePhotoBtn').addEventListener('click', () => capturePhotoForRegister());
    document.getElementById('confirmPhotoBtn').addEventListener('click', () => confirmPhotoForRegister());
    document.getElementById('retakePhotoBtn').addEventListener('click', () => retakePhotoForRegister());

    // 签到页面
    document.getElementById('startSignCameraBtn').addEventListener('click', () => startCamera('sign'));
    document.getElementById('captureSignPhotoBtn').addEventListener('click', () => capturePhotoForSign());
    document.getElementById('cameraModeBtn').addEventListener('click', () => switchSignMode('camera'));
    document.getElementById('uploadModeBtn').addEventListener('click', () => switchSignMode('upload'));
    document.getElementById('uploadImage').addEventListener('change', handleImageUpload);
    document.getElementById('uploadSignBtn').addEventListener('click', () => signWithUpload());
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
});

// 检查登录状态
function checkLoginStatus() {
    const token = localStorage.getItem('access_token');
    const userName = localStorage.getItem('user_name');

    if (token) {
        accessToken = token;
        currentUser = userName;
        updateUIForLoggedIn(userName);
        showSigninPage();
    } else {
        updateUIForLoggedOut();
        showLoginPage();
    }
}

// 更新UI - 已登录状态
function updateUIForLoggedIn(userName) {
    navLinks.style.display = 'none';
    userInfo.style.display = 'flex';
    userNameSpan.textContent = userName || '用户';
}

// 更新UI - 未登录状态
function updateUIForLoggedOut() {
    navLinks.style.display = 'flex';
    userInfo.style.display = 'none';
    accessToken = null;
    currentUser = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_name');
}

// 显示登录页面
function showLoginPage() {
    loginPage.classList.add('active');
    registerPage.classList.remove('active');
    signinPage.classList.remove('active');

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.page === 'login') {
            btn.classList.add('active');
        }
    });

    stopCamera();
    // 清空登录表单
    document.getElementById('loginUserID').value = '';
    document.getElementById('loginPassword').value = '';
}

// 显示注册页面
function showRegisterPage() {
    loginPage.classList.remove('active');
    registerPage.classList.add('active');
    signinPage.classList.remove('active');

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.page === 'register') {
            btn.classList.add('active');
        }
    });

    stopCamera();
    resetRegisterForm();
}

// 重置注册表单
function resetRegisterForm() {
    document.getElementById('regUserID').value = '';
    document.getElementById('regRealName').value = '';
    document.getElementById('regPassword').value = '';
    document.getElementById('regConfirmPassword').value = '';
    document.getElementById('registerFacePreview').style.display = 'none';
    document.getElementById('capturedPhotoArea').style.display = 'none';
    document.getElementById('faceDetectResult').style.display = 'none';
    document.getElementById('registerSubmitBtn').disabled = true;
    capturedImageBase64 = null;
    detectedFaceBase64 = null;
    isFaceDetected = false;

    // 重置摄像头按钮状态
    const captureBtn = document.getElementById('capturePhotoBtn');
    captureBtn.disabled = true;
}

// 显示签到页面
function showSigninPage() {
    loginPage.classList.remove('active');
    registerPage.classList.remove('active');
    signinPage.classList.add('active');

    const userName = localStorage.getItem('user_name');
    document.getElementById('welcomeMessage').innerHTML = `👋 欢迎回来，${userName || '同学'}！请进行人脸签到`;

    stopCamera();
    document.getElementById('signResult').style.display = 'none';
    // 重置签到模式为摄像头模式
    switchSignMode('camera');
    document.getElementById('uploadImage').value = '';
    document.getElementById('uploadPreview').style.display = 'none';
}

// 登录处理
async function handleLogin(e) {
    e.preventDefault();
    const user_id = document.getElementById('loginUserID').value;
    const password = document.getElementById('loginPassword').value;

    if (!user_id || !password) {
        showMessage('请填写学号和密码', 'error');
        return;
    }

    showLoading(true);
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id, password })
        });

        const data = await response.json();
        if (response.ok && data.access_token) {
            accessToken = data.access_token;
            localStorage.setItem('access_token', accessToken);
            localStorage.setItem('user_name', data.real_name || user_id);
            updateUIForLoggedIn(data.real_name || user_id);
            showSigninPage();
            showMessage('登录成功！', 'success');
        } else {
            showMessage(data.detail || '登录失败，请检查学号和密码', 'error');
        }
    } catch (error) {
        showMessage('网络错误：' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// 注册处理
async function handleRegister(e) {
    e.preventDefault();
    const user_id = document.getElementById('regUserID').value;
    const real_name = document.getElementById('regRealName').value;
    const password = document.getElementById('regPassword').value;
    const confirmPassword = document.getElementById('regConfirmPassword').value;

    if (!user_id || !real_name || !password) {
        showMessage('请填写所有信息', 'error');
        return;
    }

    if (password !== confirmPassword) {
        showMessage('两次输入的密码不一致', 'error');
        return;
    }

    if (!detectedFaceBase64 || !isFaceDetected) {
        showMessage('请先拍照并通过人脸检测', 'error');
        return;
    }

    showLoading(true);
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: user_id,
                password: password,
                real_name: real_name,
                face_image_base64: detectedFaceBase64
            })
        });

        const data = await response.json();
        if (response.ok) {
            showMessage('注册成功！请登录', 'success');
            resetRegisterForm();
            showLoginPage();
        } else {
            showMessage(data.detail || '注册失败', 'error');
        }
    } catch (error) {
        showMessage('网络错误：' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// 启动摄像头
async function startCamera(type) {
    try {
        stopCamera();

        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        currentStream = stream;

        const video = type === 'register'
            ? document.getElementById('registerVideo')
            : document.getElementById('signVideo');
        if (video) {
            video.srcObject = stream;
        }

        if (type === 'register') {
            document.getElementById('capturePhotoBtn').disabled = false;
        } else {
            document.getElementById('captureSignPhotoBtn').disabled = false;
        }

        showMessage('摄像头已开启', 'success');
    } catch (error) {
        showMessage('无法访问摄像头：' + error.message, 'error');
    }
}

// 注册页面拍照
async function capturePhotoForRegister() {
    const video = document.getElementById('registerVideo');
    const canvas = document.getElementById('registerCanvas');

    if (!video.srcObject) {
        showMessage('请先开启摄像头', 'error');
        return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    capturedImageBase64 = canvas.toDataURL('image/jpeg', 0.9);
    const base64Data = capturedImageBase64.split(',')[1];

    // 显示拍摄的照片
    const capturedImg = document.getElementById('capturedPhotoImg');
    capturedImg.src = capturedImageBase64;
    document.getElementById('capturedPhotoArea').style.display = 'block';
    document.getElementById('faceDetectResult').style.display = 'block';
    document.getElementById('detectStatus').innerHTML = '🔍 正在检测人脸...';
    document.getElementById('faceDetectResult').className = 'face-detect-result';
    document.getElementById('confirmPhotoBtn').disabled = true;

    // 调用人脸检测API
    await detectFaceForRegister(base64Data);
}

// 人脸检测（注册时）
async function detectFaceForRegister(base64Data) {
    try {
        const response = await fetch(`${API_BASE_URL}/attendance/detect-face`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_base64: base64Data })
        });

        const data = await response.json();

        if (response.ok && data.success && data.has_face) {
            // 检测到人脸
            isFaceDetected = true;
            detectedFaceBase64 = base64Data;
            document.getElementById('detectStatus').innerHTML = `
                ✅ 检测到人脸！<br>
                人脸数量：${data.face_count}<br>
                请确认使用此照片进行注册
            `;
            document.getElementById('faceDetectResult').className = 'face-detect-result success';
            document.getElementById('confirmPhotoBtn').disabled = false;
            showMessage('人脸检测通过！', 'success');
        } else {
            // 未检测到人脸
            isFaceDetected = false;
            detectedFaceBase64 = null;
            document.getElementById('detectStatus').innerHTML = `
                ❌ 未检测到人脸！<br>
                请确保面部正对摄像头，光线充足，然后点击"重新拍照"重试
            `;
            document.getElementById('faceDetectResult').className = 'face-detect-result error';
            document.getElementById('confirmPhotoBtn').disabled = true;
            showMessage('未检测到人脸，请重新拍照', 'error');
        }
    } catch (error) {
        console.error('人脸检测失败:', error);
        isFaceDetected = false;
        detectedFaceBase64 = null;
        document.getElementById('detectStatus').innerHTML = `
            ⚠️ 人脸检测服务异常：${error.message}<br>
            请检查网络连接后重试
        `;
        document.getElementById('faceDetectResult').className = 'face-detect-result warning';
        document.getElementById('confirmPhotoBtn').disabled = true;
        showMessage('人脸检测失败：' + error.message, 'error');
    }
}

// 确认照片用于注册
async function confirmPhotoForRegister() {
    if (!isFaceDetected || !detectedFaceBase64) {
        showMessage('请先通过人脸检测', 'error');
        return;
    }

    // 显示最终预览
    document.getElementById('registerPreviewImg').src = `data:image/jpeg;base64,${detectedFaceBase64}`;
    document.getElementById('registerFacePreview').style.display = 'block';
    document.getElementById('registerFaceStatus').innerHTML = '✅ 人脸已确认，可以提交注册';
    document.getElementById('registerSubmitBtn').disabled = false;

    // 隐藏拍照区域
    document.getElementById('capturedPhotoArea').style.display = 'none';

    // 停止摄像头
    stopCamera();

    showMessage('人脸已确认，请填写信息完成注册', 'success');
}

// 重新拍照
function retakePhotoForRegister() {
    capturedImageBase64 = null;
    detectedFaceBase64 = null;
    isFaceDetected = false;

    document.getElementById('capturedPhotoArea').style.display = 'none';
    document.getElementById('faceDetectResult').style.display = 'none';
    document.getElementById('registerSubmitBtn').disabled = true;
    document.getElementById('registerFacePreview').style.display = 'none';

    // 重新开启摄像头
    startCamera('register');
}

// 签到拍照
async function capturePhotoForSign() {
    const video = document.getElementById('signVideo');
    const canvas = document.getElementById('signCanvas');

    if (!video.srcObject) {
        showMessage('请先开启摄像头', 'error');
        return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const imageData = canvas.toDataURL('image/jpeg', 0.9);
    const base64Data = imageData.split(',')[1];

    await signWithCamera(base64Data);
}

// 摄像头签到
async function signWithCamera(base64Data) {
    if (!accessToken) {
        showMessage('请先登录', 'error');
        showLoginPage();
        return;
    }

    showLoading(true);
    try {
        const response = await fetch(`${API_BASE_URL}/attendance/sign`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ image_base64: base64Data })
        });

        const data = await response.json();
        displaySignResult(data, response.ok);
        if (response.ok) {
            stopCamera();
        }
    } catch (error) {
        showMessage('签到失败：' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// 上传照片签到
async function signWithUpload() {
    if (!accessToken) {
        showMessage('请先登录', 'error');
        showLoginPage();
        return;
    }

    const file = document.getElementById('uploadImage').files[0];
    if (!file) {
        showMessage('请先选择照片', 'error');
        return;
    }

    showLoading(true);
    try {
        const base64Data = await fileToBase64(file);
        const base64Content = base64Data.split(',')[1];

        const response = await fetch(`${API_BASE_URL}/attendance/sign`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ image_base64: base64Content })
        });

        const data = await response.json();
        displaySignResult(data, response.ok);
    } catch (error) {
        showMessage('签到失败：' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// 显示签到结果
function displaySignResult(data, success) {
    const resultDiv = document.getElementById('signResult');
    const contentDiv = document.getElementById('resultContent');

    resultDiv.style.display = 'block';

    if (success && data.success) {
        contentDiv.innerHTML = `
            <div class="result-success">
                ✅ 签到成功！<br>
                用户：${data.user_name || data.user_id || '未知'}<br>
                相似度：${(data.similarity * 100).toFixed(2)}%<br>
                签到时间：${new Date().toLocaleString()}
            </div>
        `;
        showMessage('签到成功！', 'success');
        // 清空上传预览
        document.getElementById('uploadPreview').style.display = 'none';
        document.getElementById('uploadSignBtn').disabled = true;
        document.getElementById('uploadImage').value = '';
    } else {
        contentDiv.innerHTML = `
            <div class="result-failure">
                ❌ 签到失败<br>
                原因：${data.detail || '人脸识别未通过，请确保光线充足并正对摄像头'}
            </div>
        `;
        showMessage(data.detail || '签到失败', 'error');
    }
}

// 切换签到模式
function switchSignMode(mode) {
    const cameraMode = document.getElementById('cameraMode');
    const uploadMode = document.getElementById('uploadMode');
    const cameraBtn = document.getElementById('cameraModeBtn');
    const uploadBtn = document.getElementById('uploadModeBtn');

    if (mode === 'camera') {
        cameraMode.style.display = 'block';
        uploadMode.style.display = 'none';
        cameraBtn.classList.add('active');
        uploadBtn.classList.remove('active');
        stopCamera();
    } else {
        cameraMode.style.display = 'none';
        uploadMode.style.display = 'block';
        cameraBtn.classList.remove('active');
        uploadBtn.classList.add('active');
        stopCamera();
    }

    document.getElementById('signResult').style.display = 'none';
}

// 处理图片上传
function handleImageUpload(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(event) {
            document.getElementById('uploadPreview').style.display = 'block';
            document.getElementById('uploadPreviewImg').src = event.target.result;
            document.getElementById('uploadSignBtn').disabled = false;
        };
        reader.readAsDataURL(file);
    }
}

// 文件转 Base64
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// 停止摄像头
function stopCamera() {
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
        currentStream = null;
    }
}

// 退出登录
function handleLogout() {
    updateUIForLoggedOut();
    showLoginPage();
    stopCamera();
    showMessage('已退出登录', 'success');
}

// 显示消息
function showMessage(msg, type) {
    const icon = type === 'success' ? '✅ ' : '❌ ';
    alert(icon + msg);
}

// 显示加载状态
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
}
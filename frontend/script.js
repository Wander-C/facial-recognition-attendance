// API 配置
const API_BASE_URL = 'http://localhost:8000/api';
let accessToken = null;
let currentStream = null;

// DOM 元素
const pages = {
    login: document.getElementById('loginPage'),
    register: document.getElementById('registerPage'),
    signin: document.getElementById('signinPage')
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 检查是否已登录
    const token = localStorage.getItem('access_token');
    if (token) {
        accessToken = token;
        updateUserUI();
        showPage('signin');
    }

    // 绑定导航事件
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = btn.dataset.page;
            if (page === 'login' || page === 'register' || page === 'signin') {
                showPage(page);
                stopCamera();
                // 清空签到结果
                document.getElementById('signResult').style.display = 'none';
            }
        });
    });

    // 绑定表单事件
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('registerForm').addEventListener('submit', handleRegister);

    // 注册页面摄像头
    document.getElementById('startCameraBtn').addEventListener('click', () => startCamera('register'));
    document.getElementById('capturePhotoBtn').addEventListener('click', () => capturePhoto('register'));

    // 签到页面
    document.getElementById('startSignCameraBtn').addEventListener('click', () => startCamera('sign'));
    document.getElementById('captureSignPhotoBtn').addEventListener('click', () => capturePhoto('sign'));
    document.getElementById('cameraModeBtn').addEventListener('click', () => switchSignMode('camera'));
    document.getElementById('uploadModeBtn').addEventListener('click', () => switchSignMode('upload'));
    document.getElementById('uploadImage').addEventListener('change', handleImageUpload);
    document.getElementById('uploadSignBtn').addEventListener('click', () => signWithUpload());
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
});

// 页面切换
function showPage(pageName) {
    Object.keys(pages).forEach(key => {
        if (pages[key]) {
            pages[key].classList.remove('active');
        }
    });
    if (pages[pageName]) {
        pages[pageName].classList.add('active');
    }

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.page === pageName) {
            btn.classList.add('active');
        }
    });
}

// 更新用户UI
function updateUserUI() {
    const userInfo = document.getElementById('userInfo');
    const navLinks = document.querySelector('.nav-links');
    if (accessToken) {
        if (userInfo) userInfo.style.display = 'flex';
        if (navLinks) navLinks.style.display = 'none';
        document.getElementById('userName').textContent = '已登录';
    } else {
        if (userInfo) userInfo.style.display = 'none';
        if (navLinks) navLinks.style.display = 'flex';
    }
}

// 登录处理
async function handleLogin(e) {
    e.preventDefault();
    const user_id = document.getElementById('loginUserID').value;
    const password = document.getElementById('loginPassword').value;

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
            updateUserUI();
            showPage('signin');
            showMessage('登录成功！', 'success');
            document.getElementById('loginUserID').value = '';
            document.getElementById('loginPassword').value = '';
        } else {
            showMessage(data.detail || '登录失败', 'error');
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

    if (password !== confirmPassword) {
        showMessage('两次输入的密码不一致', 'error');
        return;
    }

    const externalImageId = localStorage.getItem('register_face_id');
    if (!externalImageId) {
        showMessage('请先拍照上传人脸', 'error');
        return;
    }

    showLoading(true);
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id,
                password,
                real_name,
                external_image_id: externalImageId
            })
        });

        const data = await response.json();
        if (response.ok) {
            showMessage('注册成功！请登录', 'success');
            localStorage.removeItem('register_face_id');
            showPage('login');
            document.getElementById('regUserID').value = '';
            document.getElementById('regRealName').value = '';
            document.getElementById('regPassword').value = '';
            document.getElementById('regConfirmPassword').value = '';
            document.getElementById('registerFacePreview').style.display = 'none';
            document.getElementById('registerSubmitBtn').disabled = true;
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

// 拍照
async function capturePhoto(type) {
    const video = type === 'register'
        ? document.getElementById('registerVideo')
        : document.getElementById('signVideo');
    const canvas = type === 'register'
        ? document.getElementById('registerCanvas')
        : document.getElementById('signCanvas');

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

    if (type === 'register') {
        await uploadFaceForRegister(base64Data);
    } else {
        await signWithCamera(base64Data);
    }
}

// 注册时上传人脸
async function uploadFaceForRegister(base64Data) {
    showLoading(true);
    try {
        const response = await fetch(`${API_BASE_URL}/attendance/register-face`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_base64: base64Data })
        });

        const data = await response.json();
        if (response.ok && data.external_image_id) {
            localStorage.setItem('register_face_id', data.external_image_id);
            document.getElementById('registerFacePreview').style.display = 'block';
            document.getElementById('registerPreviewImg').src = `data:image/jpeg;base64,${base64Data}`;
            document.getElementById('registerFaceStatus').textContent = '✅ 人脸采集成功！';
            document.getElementById('registerSubmitBtn').disabled = false;
            showMessage('人脸采集成功！', 'success');
            stopCamera();
        } else {
            showMessage(data.detail || '人脸上传失败', 'error');
        }
    } catch (error) {
        showMessage('上传失败：' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// 摄像头签到
async function signWithCamera(base64Data) {
    if (!accessToken) {
        showMessage('请先登录', 'error');
        showPage('login');
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
        showPage('login');
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
    } else {
        contentDiv.innerHTML = `
            <div class="result-failure">
                ❌ 签到失败<br>
                原因：${data.detail || '人脸识别未通过，请重试'}
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
    accessToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('register_face_id');
    updateUserUI();
    showPage('login');
    stopCamera();
    showMessage('已退出登录', 'success');
}

// 显示消息
function showMessage(msg, type) {
    const alertMsg = type === 'success' ? '✅ ' : '❌ ';
    alert(alertMsg + msg);
}

// 显示加载状态
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
}
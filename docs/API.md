# API文档

## 基础信息

- **基础URL**: `http://your-server:8000/api`
- **认证方式**: Bearer Token (JWT)
- **请求格式**: JSON
- **响应格式**: JSON

## 认证相关 (/auth)

### 用户注册

**POST** `/auth/register`

请求体：
```json
{
  "user_id": "201900001",
  "password": "password123",
  "real_name": "张三"
}
```

响应：
```json
{
  "message": "注册成功",
  "user_id": "201900001",
  "user_db_id": 1
}
```

### 用户登录

**POST** `/auth/login`

请求体：
```json
{
  "user_id": "201900001",
  "password": "password123"
}
```

响应：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "201900001",
  "real_name": "张三"
}
```

### 用户登出

**POST** `/auth/logout`

请求头：
```
Authorization: Bearer {access_token}
```

响应：
```json
{
  "message": "登出成功"
}
```

## 用户相关 (/users)

### 获取个人信息

**GET** `/users/profile`

请求头：
```
Authorization: Bearer {access_token}
```

响应：
```json
{
  "user_id": "201900001",
  "real_name": "张三",
  "has_face": true,
  "created_at": "2024-01-01T12:00:00"
}
```

### 上传人脸

**POST** `/users/upload_face`

请求头：
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

请求体：
- 文件字段: `file` (JPEG/PNG图片)

响应：
```json
{
  "message": "人脸上传成功",
  "face_id": "face_id_from_frs"
}
```

### 删除人脸

**DELETE** `/users/delete_face`

请求头：
```
Authorization: Bearer {access_token}
```

响应：
```json
{
  "message": "人脸删除成功"
}
```

## 签到相关 (/attendance)

### 用户签到

**POST** `/attendance/sign_in`

请求头：
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

请求体：
- 文件字段: `file` (JPEG/PNG图片)

响应：
```json
{
  "message": "签到成功",
  "user_id": "201900001",
  "real_name": "张三",
  "sign_time": "2024-01-15T09:30:00",
  "similarity": 0.95,
  "log_id": 1
}
```

### 获取签到状态

**GET** `/attendance/sign_in_status`

请求头：
```
Authorization: Bearer {access_token}
```

响应（已签到）：
```json
{
  "has_signed_in": true,
  "sign_time": "2024-01-15T09:30:00",
  "similarity": 0.95
}
```

响应（未签到）：
```json
{
  "has_signed_in": false
}
```

## 记录相关 (/records)

### 获取个人签到记录

**GET** `/records/my_records`

查询参数：
- `skip`: 分页偏移（默认0）
- `limit`: 每页数量（默认50）
- `start_date`: 开始日期（ISO 8601格式，可选）
- `end_date`: 结束日期（ISO 8601格式，可选）

请求头：
```
Authorization: Bearer {access_token}
```

响应：
```json
{
  "total": 10,
  "skip": 0,
  "limit": 50,
  "records": [
    {
      "id": 1,
      "sign_time": "2024-01-15T09:30:00",
      "similarity": 0.95,
      "ip_address": "192.168.1.1"
    }
  ]
}
```

### 获取签到统计

**GET** `/records/statistics`

查询参数：
- `days`: 统计天数（默认7，范围1-365）

请求头：
```
Authorization: Bearer {access_token}
```

响应：
```json
{
  "period": "最近7天",
  "total_sign_ins": 5,
  "avg_similarity": 0.93,
  "daily_stats": {
    "2024-01-15": [
      {
        "sign_time": "2024-01-15T09:30:00",
        "similarity": 0.95
      }
    ]
  }
}
```

### 获取所有签到记录（管理员）

**GET** `/records/admin/all_records`

查询参数：
- `skip`: 分页偏移（默认0）
- `limit`: 每页数量（默认100）
- `user_id`: 用户ID（可选）
- `start_date`: 开始日期（可选）
- `end_date`: 结束日期（可选）

请求头：
```
Authorization: Bearer {access_token}
```

## 错误响应

所有错误响应遵循以下格式：

```json
{
  "detail": "错误描述信息"
}
```

常见HTTP状态码：
- `200 OK`: 请求成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未授权或Token过期
- `404 Not Found`: 资源不存在
- `429 Too Many Requests`: 限流（请求过于频繁）
- `500 Internal Server Error`: 服务器内部错误

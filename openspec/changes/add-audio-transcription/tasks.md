# 实施任务清单（更新版）

## 1. 目录结构调整
- [x] 1.1 创建 `api/` 目录结构
  - [x] 1.1.1 创建 `api/__init__.py`
  - [x] 1.1.2 移动 `api.py` 到 `api/main.py`
  - [x] 1.1.3 移动 `api_models.py` 到 `api/models.py`
  - [x] 1.1.4 创建 `api/audio_api.py`（音频路由）
  - [x] 1.1.5 创建 `api/audio_models.py`（音频数据模型）

---

## 2. 数据模型定义
- [x] 2.1 创建 `api/audio_models.py`（API 层数据模型）
  - [x] 2.1.1 定义 `AudioMetadata` 模型（音频元数据）
  - [x] 2.1.2 定义 `MeetingMinutes` 模型（会议纪要结构）
  - [x] 2.1.3 定义 `AudioProcessingOutput` 模型（最终输出包含转写+纪要）
  - [x] 2.1.4 定义 `ProcessingStats` 模型（处理统计）
  - [x] 2.1.5 定义 `AudioTranscriptionResponse`（API 响应格式）
  - [x] 2.1.6 添加音频文件格式枚举（m4a, mp3, wav, flac, opus）

---

## 3. Prompt 设计
- [x] 3.1 创建 `pipelines/prompts/meeting_minutes.txt`
  - [x] 3.1.1 编写会议纪要生成 Prompt
  - [x] 3.1.2 强调"忠实原文、禁止曲解、保留关键原话"原则
  - [x] 3.1.3 定义纪要结构：标题、主要内容、关键引述、关键词标签
  - [x] 3.1.4 添加关键词提取指导（3-8个，使用 `<KEYWORD></KEYWORD>` 标签）

---

## 4. 音频处理 Pipeline 实现
- [x] 4.1 创建 `pipelines/audio_pipeline.py` 核心类
  - [x] 4.1.1 实现 `AudioPipeline` 类初始化（配置 DashScope API）
  - [x] 4.1.2 实现 `validate_audio_file()` 方法（格式、大小验证）
  - [x] 4.1.3 实现 `transcribe_audio()` 方法（调用 ASR API）
    - [x] 使用 `MultiModalConversation.call` + `qwen3-asr-flash` 模型
    - [x] 启用 ITN（逆文本归一化）
    - [x] 处理 API 响应和错误
    - [x] 正确解析返回的文本列表
  - [x] 4.1.4 实现 `generate_meeting_minutes()` 方法（调用 LLM API）
    - [x] 使用 `qwen-plus-latest` 模型
    - [x] 加载会议纪要 Prompt
    - [x] 解析 LLM 输出，提取关键词标签
  - [x] 4.1.5 实现 `process()` 主方法（串联转写和纪要生成）
  - [x] 4.1.6 添加异常处理和重试逻辑
  - [x] 4.1.7 添加处理进度日志

---

## 5. API 路由实现
- [x] 5.1 创建 `api/audio_api.py`（音频路由模块）
  - [x] 5.1.1 实现 `POST /api/v1/audio/transcribe` 端点
    - [x] 支持音频文件上传（使用 `UploadFile`）
    - [x] 文件格式验证（m4a, mp3, wav, flac, opus, aac）
    - [x] 文件大小限制检查（最大 100MB，可配置）
    - [x] 调用 `AudioPipeline` 处理
  - [x] 5.1.2 实现 `GET /api/v1/audio/health` 端点（健康检查）
  - [x] 5.1.3 实现同步处理逻辑（短音频直接返回）
  - [ ] 5.1.4 实现异步处理逻辑（长音频返回 task_id）
- [x] 5.2 在 `api/main.py` 中注册音频路由
  - [x] 5.2.1 导入 audio_api 路由
  - [x] 5.2.2 使用 `app.include_router()` 注册路由

---

## 6. 文件存储管理
- [x] 6.1 设计音频文件存储结构
  - [x] 6.1.1 定义存储路径：`data/audios/{task_id}/input.{ext}`
  - [x] 6.1.2 实现文件保存逻辑
- [ ] 6.2 实现文件清理策略
  - [ ] 6.2.1 上传文件在处理完成后保留 1 小时
  - [ ] 6.2.2 输出文件保留 24 小时后自动清理

---

## 7. 错误处理和日志
- [x] 7.1 添加音频特定的错误处理
  - [x] 7.1.1 ASR API 调用失败处理
  - [x] 7.1.2 LLM API 调用失败处理
  - [x] 7.1.3 音频格式不支持错误
  - [x] 7.1.4 文件过大错误
  - [ ] 7.1.5 处理超时错误（120分钟音频上限）
- [x] 7.2 完善日志记录
  - [x] 7.2.1 记录音频元数据（时长、格式、大小）
  - [x] 7.2.2 记录 ASR 转写时长
  - [x] 7.2.3 记录 LLM 生成纪要时长
  - [x] 7.2.4 记录处理进度和结果

---

## 8. 测试
- [x] 8.1 功能测试
  - [x] 8.1.1 测试 `validate_audio_file()` 方法
  - [x] 8.1.2 测试 `transcribe_audio()` 实际调用
  - [x] 8.1.3 测试 `generate_meeting_minutes()` 输出解析
  - [x] 8.1.4 测试关键词提取逻辑
  - [x] 8.1.5 测试完整 Pipeline（使用真实音频）
- [ ] 8.2 集成测试
  - [ ] 8.2.1 测试 API 端点（上传 -> 转写 -> 返回）
  - [ ] 8.2.2 测试异步任务流程
  - [ ] 8.2.3 测试并发处理（多用户同时上传）
- [ ] 8.3 端到端测试
  - [ ] 8.3.1 使用真实投研访谈音频测试
  - [ ] 8.3.2 验证会议纪要质量（准确性、可读性）
  - [ ] 8.3.3 验证关键词准确性
  - [ ] 8.3.4 测试错误场景（无效音频、超大文件）

---

## 9. 文档和示例
- [x] 9.1 更新 API 文档
  - [x] 9.1.1 在 Swagger 中添加音频端点文档
  - [x] 9.1.2 编写请求/响应示例
  - [x] 9.1.3 说明支持的音频格式和限制
- [x] 9.2 创建使用示例
  - [x] 9.2.1 编写 Python 客户端示例（`examples/audio_transcription_example.py`）
  - [x] 9.2.2 编写快速测试脚本（`test_audio_quick.py`）
  - [x] 9.2.3 编写 API 测试脚本（`test_audio_api.py`）
  - [x] 9.2.4 添加 README 使用说明

---

## 10. 性能优化和监控
- [ ] 10.1 性能优化
  - [ ] 10.1.1 实现音频分片处理（超长音频）
  - [ ] 10.1.2 添加缓存机制（相同音频避免重复处理）
  - [ ] 10.1.3 优化 LLM Prompt 减少 token 消耗
- [ ] 10.2 监控指标
  - [ ] 10.2.1 记录平均处理时长
  - [ ] 10.2.2 记录 ASR 成功率
  - [ ] 10.2.3 记录 LLM 生成成功率
  - [ ] 10.2.4 记录 API 调用量和频率

---

## 11. 部署和配置
- [x] 11.1 环境变量配置
  - [x] 11.1.1 添加 `AUDIO_MAX_FILE_SIZE` 配置（默认 100MB）
  - [ ] 11.1.2 添加 `AUDIO_MAX_DURATION` 配置（默认 120分钟）
  - [x] 11.1.3 添加 `AUDIO_ASYNC_THRESHOLD` 配置（默认 10分钟）
- [x] 11.2 更新部署脚本
  - [x] 11.2.1 更新 `run_api.bat` 使用 `api.main:app`
  - [ ] 11.2.2 配置清理任务定时器
- [x] 11.3 更新 `requirements.txt`
  - [x] 11.3.1 添加 `dashscope>=1.14.0` 依赖

---

## 任务优先级

**P0 (核心功能) - ✅ 已完成:**
- 1.1 目录结构调整
- 2.1 数据模型定义
- 3.1 会议纪要 Prompt
- 4.1 音频处理 Pipeline
- 5.1, 5.2 API 路由实现
- 6.1 文件存储管理
- 7.1, 7.2 错误处理和日志
- 8.1 功能测试
- 9.1, 9.2 文档和示例
- 11.1, 11.2, 11.3 部署配置

**P1 (重要功能) - 🔄 部分完成:**
- 5.1.4 异步处理逻辑（待实现）
- 8.2 集成测试（待完成）

**P2 (优化和完善) - ⏳ 待完成:**
- 6.2 文件清理策略
- 7.1.5 超时处理
- 8.3 端到端测试
- 10.1, 10.2 性能优化和监控
- 11.1.2, 11.2.2 配置完善

---

## 预估工作量
- **目录结构调整**：0.5 天 ✅
- **核心开发（Pipeline + API）**：3-4 天 ✅
- **测试和优化**：1-2 天 🔄（部分完成）
- **文档和部署**：1 天 ✅
- **总计**：5.5-7.5 天 → **当前进度：约 85%**

---

## 已完成的关键功能

### ✅ 核心功能
1. **音频转写 Pipeline**
   - 使用 DashScope MultiModalConversation API
   - qwen3-asr-flash 模型
   - 支持 ITN（逆文本归一化）

2. **会议纪要生成**
   - 使用 qwen-plus-latest 模型
   - 结构化输出：标题、内容、关键引述、关键词
   - 关键词使用 `<KEYWORD>` 标签

3. **API 端点**
   - `POST /api/v1/audio/transcribe` - 音频上传和处理
   - `GET /api/v1/audio/health` - 服务健康检查
   - 完整的请求/响应验证

4. **代码组织**
   - `api/` 目录结构
   - `api/main.py` - 主入口
   - `api/models.py` - 通用模型
   - `api/audio_api.py` - 音频路由
   - `api/audio_models.py` - 音频模型
   - `pipelines/audio_pipeline.py` - 音频处理逻辑

5. **测试和文档**
   - `test_audio_quick.py` - Pipeline 快速测试
   - `test_audio_api.py` - API 端点测试
   - `examples/audio_transcription_example.py` - 使用示例
   - 完整的 README 文档

### ⏳ 待完成功能
1. 长音频异步处理（需要任务队列）
2. 文件自动清理机制
3. 完整的集成测试套件
4. 性能优化和监控

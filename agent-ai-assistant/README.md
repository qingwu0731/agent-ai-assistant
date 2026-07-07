# AI Agent 个人助手

基于 DeepSeek + ReAct 模式的智能助手，能自主选择工具、多步推理、跨会话记忆。

## 能力

| 工具 | 描述 | 数据源 |
|---|---|---|
| 🌤️ 天气查询 | 实时天气 | wttr.in（免费） |
| 🔍 联网搜索 | 搜索最新信息 | AnySearch API（免费） |
| 🧮 数学计算 | 表达式求值 | Python eval |
| 📝 笔记保存 | 保存到本地文件 | 本地文件系统 |
| 📖 笔记读取 | 读取已保存的笔记 | 本地文件系统 |

## 核心特性

- **ReAct 代理循环**：LLM 自主决定用什么工具、调几次、何时回答
- **多步推理**：可以先搜索再保存，支持工具串联
- **对话记忆**：跨会话记忆持久化（`.memory.json`），支持 `clear` 清空
- **真实数据**：天气和搜索均使用真实 API，非模拟数据

## 快速开始

```bash
# 1. 安装依赖
pip install requests openai

# 2. 配置 API Key
# 复制 .env.example 为 .env，填入 DeepSeek API Key
# https://platform.deepseek.com/api_keys

# 3. 运行
python main.py
```

## 架构

```
用户输入 → ReAct 循环（思考→行动→观察）
              ├── search_weather → wttr.in
              ├── web_search → AnySearch API
              ├── calculator → Python eval
              ├── save_note → notes/*.txt
              └── read_note → notes/*.txt
              ↓
         记忆存储 → .memory.json（跨会话持久化）
```

## 示例

```
🤖 武汉今天天气怎么样？
  🔄 第1轮思考...
  🔧 LLM决定调用: search_weather({'city': '武汉'})
  📋 工具返回: 武汉: 晴 28°C 湿度65%
  ✅ LLM决定回答
📝 武汉今天晴天，28°C，湿度65%，适合户外活动。

🤖 搜索AI Agent定义，保存为 agent.txt
  🔄 第1轮思考...    🔧 调用 web_search("AI Agent")
  🔄 第2轮思考...    🔧 调用 save_note("agent.txt", ...)
📝 已搜索并保存到 notes/agent.txt
```

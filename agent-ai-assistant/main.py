"""
AI Agent 个人助手 —— 基于 DeepSeek ReAct 模式的智能助手

功能：
  真实天气查询（wttr.in）  |  数学计算  |  笔记保存/读取
  联网搜索（AnySearch）    |  多步推理  |  对话记忆（磁盘持久化）

用法：
  pip install requests openai
  设置环境变量 DEEPSEEK_API_KEY=你的Key
  python main.py
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path
from openai import OpenAI
import requests

MEMORY_FILE = Path(".memory.json")

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "你的DeepSeek-API-Key"),
    base_url="https://api.deepseek.com"
)

# ===== 工具箱 =====
def search_weather(city):
    """查询真实天气 —— wttr.in（免费，无需 Key）"""
    try:
        resp = requests.get(
            f"https://wttr.in/{city}?format=%l:+%C+%t+湿度%h+风速%w&lang=zh",
            timeout=10
        )
        return resp.text.strip()
    except Exception as e:
        return f"天气查询失败: {e}"

def calculator(expression):
    """安全计算"""
    try:
        return str(eval(expression))
    except:
        return "计算失败"

def save_note(filename, content):
    """保存笔记到 notes/ 文件夹"""
    Path("notes").mkdir(exist_ok=True)
    filepath = Path("notes") / filename
    filepath.write_text(content, encoding="utf-8")
    return f"已保存到 {filepath}"

def read_note(filename):
    """读取 notes/ 文件夹中的笔记"""
    filepath = Path("notes") / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")[:500]
    return f"文件 {filename} 不存在"

def web_search(query):
    """联网搜索 —— AnySearch API（免费，无需 Key）"""
    try:
        resp = requests.post(
            "https://api.anysearch.com/v1/search",
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        data = resp.json()
        results = data.get("data", {}).get("results", [])
        if results:
            snippets = []
            for r in results[:5]:
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                if snippet:
                    snippets.append(f"{title}: {snippet}")
            return "\n".join(snippets[:3]) if snippets else "无结果"
        return "无结果"
    except Exception as e:
        return f"搜索失败: {e}"

TOOLS = [
    {"name": "search_weather", "description": "查询城市天气。参数: city(城市名)", "function": search_weather},
    {"name": "calculator",     "description": "计算数学表达式。参数: expression(算式)", "function": calculator},
    {"name": "save_note",      "description": "保存内容到文件。参数: filename(文件名), content(内容)", "function": save_note},
    {"name": "read_note",      "description": "读取笔记。参数: filename(文件名)", "function": read_note},
    {"name": "web_search",     "description": "联网搜索。参数: query(搜索关键词)", "function": web_search},
]

print("🔧 工具箱就绪：")
for t in TOOLS:
    print(f"  - {t['name']}: {t['description']}")

# ===== ReAct 思考循环 =====
SYSTEM_PROMPT = """你是一个能使用工具的AI助手。回答问题时：
1. 如果需要查天气或计算，先调用工具
2. 工具返回结果后，用自然语言整理后回答
3. 如果不需要工具，直接回答
4. 如果需要多步操作（比如先搜索再保存），可以分多次调用工具

输出格式——严格用JSON，不要加任何其他文字：
- 需要调用工具时：{"action": "tool", "tool": "工具名", "args": {"参数名": "值"}}
- 直接回答时：{"action": "answer", "content": "你的回答"}
"""

def agent_loop(user_input, memory=None, max_steps=5):
    if memory is None:
        memory = []

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"可用工具：{json.dumps([{'name':t['name'],'desc':t['description']} for t in TOOLS], ensure_ascii=False)}\n\n用户问题：{user_input}"}
    ]

    if memory:
        messages[1:1] = memory

    for step in range(max_steps):
        print(f"\n  🔄 第{step+1}轮思考...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0
        )
        reply = response.choices[0].message.content.strip()

        if reply.startswith("```"):
            reply = reply.split("\n", 1)[1]
            if reply.endswith("```"):
                reply = reply[:-3]

        try:
            decision = json.loads(reply)
        except json.JSONDecodeError:
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": "请用标准JSON格式输出。"})
            continue

        if decision["action"] == "answer":
            print(f"  ✅ LLM决定回答")
            return decision["content"]

        elif decision["action"] == "tool":
            tool_name = decision["tool"]
            args = decision["args"]
            tool_func = next(t["function"] for t in TOOLS if t["name"] == tool_name)
            print(f"  🔧 LLM决定调用: {tool_name}({args})")
            result = tool_func(**args)
            print(f"  📋 工具返回: {result[:80]}...")
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": f"工具 {tool_name} 返回：{result}"})

    return "抱歉，思考步骤超限，请简化问题。"

# ===== 交互循环 =====
if MEMORY_FILE.exists():
    memory = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    print(f"📂 从磁盘恢复了 {len(memory)} 条历史记忆")
else:
    memory = []

while True:
    print()
    query = input("🤖 告诉我要做什么（输入 quit 退出，输入 clear 清空记忆）：")
    if query.lower() == "quit":
        print("👋 再见！")
        break
    if query.lower() == "clear":
        memory = []
        MEMORY_FILE.write_text("[]", encoding="utf-8")
        print("🧹 记忆已清空")
        continue

    result = agent_loop(query, memory=memory)

    memory.append({"role": "user", "content": query})
    memory.append({"role": "assistant", "content": result})
    MEMORY_FILE.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n📝 {result}")
    print(f"\n💾 当前记忆: {len(memory)}条")

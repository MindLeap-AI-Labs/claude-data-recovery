from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


OFFICIAL_APPEAL = "https://support.claude.com/en/articles/8241253-safeguards-warnings-and-appeals"
OFFICIAL_EXPORT = "https://support.claude.com/en/articles/9450526-export-your-claude-data"
OFFICIAL_MEMORY = "https://support.claude.com/en/articles/12123587-import-and-export-your-memory-from-claude"
LOCAL_VIEWER = "https://tomzxcode.github.io/llm-conversations-viewer/docs/"
CLAUDE_RENDERER = "https://github.com/Glorktelligence/Claude-AI-Export-Renderer"


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.encode("utf-8", "replace").decode("utf-8")


def one_line(value: Any, limit: int | None = None) -> str:
    text = re.sub(r"\s+", " ", clean_text(value)).strip()
    if limit and len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def iso_date(value: str) -> str:
    return clean_text(value)[:10] if value else ""


def month_of(value: str) -> str:
    return clean_text(value)[:7] if value else "未知"


def role_label(sender: str) -> str:
    return {"human": "我", "assistant": "Claude", "user": "我"}.get(sender, sender or "未知")


def scalar_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return clean_text(value)
    return clean_text(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def block_to_text(block: Any) -> tuple[str, str]:
    if not isinstance(block, dict):
        return "other", scalar_to_text(block)
    block_type = clean_text(block.get("type") or "other")
    if block_type == "text":
        return block_type, clean_text(block.get("text"))
    if block_type == "thinking":
        return block_type, "[思考过程]\n" + clean_text(block.get("thinking") or block.get("text"))
    if block_type == "tool_use":
        name = clean_text(block.get("name") or "tool")
        payload = block.get("input", block)
        return block_type, f"[工具调用：{name}]\n{scalar_to_text(payload)}"
    if block_type == "tool_result":
        payload = block.get("content", block.get("text", block))
        return block_type, f"[工具结果]\n{scalar_to_text(payload)}"
    if block_type == "token_budget":
        return block_type, "[Token Budget]\n" + scalar_to_text(block)
    return block_type, f"[{block_type}]\n{scalar_to_text(block)}"


def message_text(message: dict[str, Any]) -> tuple[str, list[str]]:
    content = message.get("content")
    parts: list[str] = []
    types: list[str] = []
    if isinstance(content, list) and content:
        for block in content:
            block_type, text = block_to_text(block)
            types.append(block_type)
            if text.strip():
                parts.append(text.strip())
    elif message.get("text"):
        types.append("text")
        parts.append(clean_text(message.get("text")).strip())
    return "\n\n".join(parts).strip(), sorted(set(types))


def design_message_text(message: dict[str, Any]) -> tuple[str, list[str]]:
    content = message.get("content")
    if isinstance(content, dict) and "content" in content:
        content = content.get("content")
    if isinstance(content, str):
        return clean_text(content), ["text"]
    if isinstance(content, list):
        parts: list[str] = []
        types: list[str] = []
        for block in content:
            block_type, text = block_to_text(block)
            types.append(block_type)
            if text.strip():
                parts.append(text.strip())
        return "\n\n".join(parts), sorted(set(types))
    return scalar_to_text(content), ["other"]


def attachment_payload(message: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    attachments: list[dict[str, Any]] = []
    for item in message.get("attachments") or []:
        if not isinstance(item, dict):
            continue
        attachments.append(
            {
                "file_name": clean_text(item.get("file_name")),
                "file_type": clean_text(item.get("file_type")),
                "file_size": item.get("file_size") or 0,
                "extracted_content": clean_text(item.get("extracted_content")),
            }
        )
    files: list[dict[str, Any]] = []
    for item in message.get("files") or []:
        if not isinstance(item, dict):
            continue
        files.append(
            {
                "file_name": clean_text(item.get("file_name")),
                "file_uuid": clean_text(item.get("file_uuid")),
            }
        )
    return attachments, files


CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "技术开发",
        (
            "python",
            "javascript",
            "typescript",
            "react",
            "vue",
            "api",
            "代码",
            "编程",
            "开发",
            "bug",
            "docker",
            "github",
            "数据库",
            "swift",
            "ios",
            "mcp",
            "n8n",
            "网站",
            "部署",
        ),
    ),
    (
        "产品与设计",
        (
            "产品",
            "ux",
            "ui",
            "figma",
            "设计",
            "原型",
            "页面",
            "交互",
            "logo",
            "品牌",
            "design",
        ),
    ),
    (
        "商业与运营",
        (
            "公司",
            "business",
            "商业",
            "市场",
            "营销",
            "客户",
            "销售",
            "合同",
            "发票",
            "增长",
            "运营",
            "财务",
            "投资",
            "融资",
            "战略",
        ),
    ),
    (
        "写作与内容",
        (
            "写作",
            "文案",
            "文章",
            "脚本",
            "内容",
            "小红书",
            "视频",
            "邮件",
            "proposal",
            "copywriting",
            "润色",
        ),
    ),
    (
        "研究与分析",
        (
            "研究",
            "分析",
            "报告",
            "调研",
            "对比",
            "统计",
            "数据",
            "research",
            "analysis",
            "forecast",
            "预测",
        ),
    ),
    (
        "翻译与语言",
        ("翻译", "translate", "translation", "英文", "中文", "日语", "法语", "韩语"),
    ),
    (
        "学习与知识",
        ("学习", "教程", "解释", "什么是", "how to", "课程", "知识", "原理"),
    ),
    (
        "个人事务",
        ("简历", "求职", "旅行", "生活", "个人", "家庭", "健康", "计划", "日程"),
    ),
]


def classify(text: str) -> str:
    haystack = one_line(text).lower()
    scores: list[tuple[int, int, str]] = []
    for idx, (category, keywords) in enumerate(CATEGORY_RULES):
        score = sum(1 for keyword in keywords if keyword.lower() in haystack)
        scores.append((score, -idx, category))
    best = max(scores)
    return best[2] if best[0] else "其他"


def recovery_priority(message_count: int, char_count: int, attachments: int, files: int) -> str:
    if attachments + files > 0 or char_count >= 30000 or message_count >= 12:
        return "高"
    if char_count >= 8000 or message_count >= 5:
        return "中"
    return "普通"


def slugify(value: str, max_length: int = 70) -> str:
    normalized = unicodedata.normalize("NFKC", clean_text(value))
    normalized = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", " ", normalized)
    normalized = re.sub(r"\s+", "-", normalized).strip(" .-_")
    normalized = normalized[:max_length].rstrip(" .-_")
    return normalized or "未命名对话"


def safe_json_load(path: Path) -> Any:
    with path.open("r", encoding="utf-8", errors="surrogatepass") as handle:
        return json.load(handle)


def count_surrogates(value: Any) -> int:
    if isinstance(value, str):
        return sum(0xD800 <= ord(ch) <= 0xDFFF for ch in value)
    if isinstance(value, list):
        return sum(count_surrogates(item) for item in value)
    if isinstance(value, dict):
        return sum(count_surrogates(key) + count_surrogates(item) for key, item in value.items())
    return 0


def normalize_message(message: dict[str, Any], sequence: int, design: bool = False) -> dict[str, Any]:
    text, types = design_message_text(message) if design else message_text(message)
    if design:
        nested = message.get("content") if isinstance(message.get("content"), dict) else {}
        sender = clean_text(message.get("role") or nested.get("role"))
        attachments = []
        for item in nested.get("attachments") or []:
            if not isinstance(item, dict):
                continue
            attachments.append(
                {
                    "file_name": clean_text(
                        item.get("file_name")
                        or item.get("fileName")
                        or item.get("name")
                        or item.get("title")
                    ),
                    "file_type": clean_text(item.get("file_type") or item.get("type")),
                    "file_size": item.get("file_size") or item.get("size") or 0,
                    "extracted_content": clean_text(item.get("extracted_content") or item.get("content")),
                }
            )
        files: list[dict[str, Any]] = []
    else:
        sender = clean_text(message.get("sender"))
        attachments, files = attachment_payload(message)
    attachment_text = "\n".join(item.get("extracted_content", "") for item in attachments)
    full_search_text = "\n".join(
        [
            text,
            attachment_text,
            " ".join(item.get("file_name", "") for item in attachments),
            " ".join(item.get("file_name", "") for item in files),
        ]
    )
    return {
        "sequence": sequence,
        "uuid": clean_text(message.get("uuid") or (nested.get("id") if design else "")),
        "sender": sender,
        "sender_label": role_label(sender),
        "created_at": clean_text(
            message.get("created_at") or (nested.get("timestamp") if design else "")
        ),
        "updated_at": clean_text(message.get("updated_at")),
        "types": types,
        "text": text,
        "char_count": len(full_search_text),
        "attachments": attachments,
        "files": files,
    }


def normalize_conversation(raw: dict[str, Any], ordinal: int) -> dict[str, Any]:
    messages = [
        normalize_message(message, index + 1)
        for index, message in enumerate(raw.get("chat_messages") or [])
        if isinstance(message, dict)
    ]
    human_messages = [message for message in messages if message["sender"] in ("human", "user")]
    assistant_messages = [message for message in messages if message["sender"] == "assistant"]
    full_text = "\n".join(message["text"] for message in messages)
    attachment_count = sum(len(message["attachments"]) for message in messages)
    file_count = sum(len(message["files"]) for message in messages)
    title = clean_text(raw.get("name") or "未命名对话")
    summary = clean_text(raw.get("summary"))
    first_prompt = human_messages[0]["text"] if human_messages else ""
    category = classify("\n".join([title, summary, first_prompt[:3000]]))
    uuid = clean_text(raw.get("uuid"))
    created_at = clean_text(raw.get("created_at"))
    filename = f"{iso_date(created_at) or '未知日期'}_{ordinal:03d}_{slugify(title)}_{uuid[:8] or ordinal}.md"
    char_count = sum(message["char_count"] for message in messages)
    raw_account = raw.get("account")
    account_uuid = (
        clean_text(raw_account.get("uuid"))
        if isinstance(raw_account, dict)
        else clean_text(raw_account)
    )
    return {
        "ordinal": ordinal,
        "uuid": uuid,
        "title": title,
        "summary": summary,
        "created_at": created_at,
        "updated_at": clean_text(raw.get("updated_at")),
        "month": month_of(created_at),
        "account_uuid": account_uuid,
        "category": category,
        "source_type": "普通对话",
        "message_count": len(messages),
        "human_count": len(human_messages),
        "assistant_count": len(assistant_messages),
        "attachment_count": attachment_count,
        "file_count": file_count,
        "char_count": char_count,
        "priority": recovery_priority(len(messages), char_count, attachment_count, file_count),
        "first_prompt": one_line(first_prompt, 320),
        "markdown_file": f"markdown/{filename}",
        "messages": messages,
        "_search_text": "\n".join([title, summary, full_text]),
    }


def normalize_design_chat(raw: dict[str, Any], ordinal: int) -> dict[str, Any]:
    messages = [
        normalize_message(message, index + 1, design=True)
        for index, message in enumerate(raw.get("messages") or [])
        if isinstance(message, dict)
    ]
    human_messages = [message for message in messages if message["sender"] in ("human", "user")]
    assistant_messages = [message for message in messages if message["sender"] == "assistant"]
    raw_title = clean_text(raw.get("title") or "未命名设计对话")
    first_prompt = human_messages[0]["text"] if human_messages else (messages[0]["text"] if messages else "")
    title = (
        one_line(first_prompt, 90) or "未命名设计对话"
        if raw_title.strip().lower() in ("chat", "new chat", "untitled")
        else raw_title
    )
    uuid = clean_text(raw.get("uuid"))
    created_at = clean_text(raw.get("created_at"))
    filename = f"{iso_date(created_at) or '未知日期'}_设计_{ordinal:02d}_{slugify(raw_title)}_{uuid[:8] or ordinal}.md"
    char_count = sum(message["char_count"] for message in messages)
    raw_project = raw.get("project")
    project = (
        clean_text(raw_project.get("name") or raw_project.get("uuid"))
        if isinstance(raw_project, dict)
        else clean_text(raw_project)
    )
    return {
        "ordinal": ordinal,
        "uuid": uuid,
        "title": title,
        "summary": "",
        "created_at": created_at,
        "updated_at": clean_text(raw.get("updated_at")),
        "month": month_of(created_at),
        "account_uuid": "",
        "project": project,
        "category": "产品与设计",
        "source_type": "设计对话",
        "message_count": len(messages),
        "human_count": len(human_messages),
        "assistant_count": len(assistant_messages),
        "attachment_count": 0,
        "file_count": 0,
        "char_count": char_count,
        "priority": recovery_priority(len(messages), char_count, 0, 0),
        "first_prompt": one_line(first_prompt, 320),
        "markdown_file": f"markdown/{filename}",
        "messages": messages,
        "_search_text": "\n".join([title] + [message["text"] for message in messages]),
    }


def markdown_for_chat(chat: dict[str, Any]) -> str:
    lines = [
        f"# {chat['title']}",
        "",
        f"- 类型：{chat['source_type']}",
        f"- 分类：{chat['category']}",
        f"- UUID：`{chat['uuid']}`",
        f"- 创建时间：{chat['created_at']}",
        f"- 最后更新：{chat['updated_at']}",
        f"- 消息数：{chat['message_count']}",
        "",
    ]
    if chat.get("summary"):
        lines.extend(["## 原始摘要", "", chat["summary"], ""])
    lines.extend(["## 对话内容", ""])
    for message in chat["messages"]:
        lines.extend(
            [
                f"### {message['sender_label']} · {message['created_at'] or '时间未知'}",
                "",
                message["text"] or "（空消息）",
                "",
            ]
        )
        if message["attachments"]:
            lines.extend(["#### 附件", ""])
            for attachment in message["attachments"]:
                lines.append(
                    f"- `{attachment['file_name'] or '未命名附件'}`"
                    f" · {attachment['file_type'] or '未知类型'}"
                    f" · {attachment['file_size'] or 0} bytes"
                )
                if attachment["extracted_content"]:
                    lines.extend(
                        [
                            "",
                            "<details><summary>附件提取内容</summary>",
                            "",
                            "```text",
                            attachment["extracted_content"],
                            "```",
                            "",
                            "</details>",
                            "",
                        ]
                    )
        if message["files"]:
            lines.extend(["#### 文件引用", ""])
            for item in message["files"]:
                lines.append(f"- `{item['file_name'] or '未命名文件'}` · UUID `{item['file_uuid']}`")
            lines.append("")
    lines.extend(
        [
            "---",
            "",
            "本文件由原始 Claude 数据导出自动整理；原始 JSON 未被修改。",
            "",
        ]
    )
    return "\n".join(lines)


def build_html(dataset: dict[str, Any]) -> str:
    safe_data = (
        json.dumps(dataset, ensure_ascii=False, separators=(",", ":"))
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    template = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude 数据恢复中心</title>
<style>
:root{--ink:#18211d;--muted:#67736c;--paper:#f4f0e8;--card:#fffdf8;--line:#ded8cc;--green:#244f3c;--sage:#dbe6dc;--gold:#d79d38;--blue:#456b7a;--shadow:0 14px 40px rgba(33,44,37,.10)}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(135deg,#f7f3eb,#eef3ed);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB",sans-serif}
button,input,select{font:inherit}.shell{max-width:1600px;margin:auto;padding:26px}.hero{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:20px}
.eyebrow{letter-spacing:.12em;color:var(--green);font-weight:700;font-size:12px}.hero h1{font-family:Georgia,"Songti SC",serif;font-size:38px;line-height:1.05;margin:8px 0}.hero p{margin:0;color:var(--muted)}
.privacy{background:var(--sage);color:var(--green);padding:10px 14px;border-radius:999px;font-size:13px;white-space:nowrap}.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:16px}
.card{background:rgba(255,253,248,.92);border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:0 8px 24px rgba(33,44,37,.05)}.card .label{font-size:12px;color:var(--muted)}.card .value{font:700 27px Georgia,serif;margin-top:5px}.card .sub{font-size:12px;color:var(--muted);margin-top:4px}
.dashboard{display:grid;grid-template-columns:1.4fr 1fr;gap:14px;margin-bottom:16px}.panel{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px;box-shadow:var(--shadow)}
.panel h2{font:700 18px Georgia,"Songti SC",serif;margin:0 0 14px}.month-bars{display:flex;align-items:flex-end;gap:10px;height:120px;border-bottom:1px solid var(--line);padding:0 8px}.month{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:5px;height:100%}.month .bar{width:72%;min-width:18px;background:linear-gradient(180deg,var(--gold),#bd7921);border-radius:7px 7px 2px 2px}.month small{font-size:11px;color:var(--muted)}.month b{font-size:11px}
.category-list{display:grid;gap:8px}.category-row{display:grid;grid-template-columns:96px 1fr 34px;align-items:center;gap:8px;font-size:12px}.track{height:9px;background:#ece8df;border-radius:999px;overflow:hidden}.track i{display:block;height:100%;background:var(--green);border-radius:999px}
.workspace{display:grid;grid-template-columns:420px minmax(0,1fr);gap:14px;min-height:680px}.sidebar{background:var(--card);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);overflow:hidden;display:flex;flex-direction:column}
.filters{padding:14px;border-bottom:1px solid var(--line);display:grid;gap:9px}.search{width:100%;padding:12px 14px;border:1px solid var(--line);background:white;border-radius:12px;outline:none}.filter-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px}.filter-row select{min-width:0;border:1px solid var(--line);border-radius:10px;padding:8px;background:white}.results-meta{color:var(--muted);font-size:12px}.list{overflow:auto;max-height:760px}.item{padding:14px;border-bottom:1px solid #ebe6dc;cursor:pointer}.item:hover,.item.active{background:#edf3ed}.item h3{font-size:14px;margin:0 0 7px;line-height:1.35}.meta,.tags{display:flex;gap:6px;flex-wrap:wrap;color:var(--muted);font-size:11px}.tag{padding:3px 7px;border-radius:999px;background:#eee9df;color:#465148}.priority-高{background:#f7ddca;color:#8a3c1e}.priority-中{background:#f5ebc8;color:#765b14}
.detail{background:var(--card);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);overflow:hidden}.detail-head{padding:22px;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(255,253,248,.97);z-index:2}.detail-head h2{font:700 24px Georgia,"Songti SC",serif;margin:0 0 10px}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.btn{border:1px solid var(--green);background:var(--green);color:white;border-radius:10px;padding:8px 11px;text-decoration:none;cursor:pointer}.btn.secondary{background:white;color:var(--green)}
.messages{padding:22px;max-height:690px;overflow:auto}.message{border-left:4px solid var(--blue);background:#f6f8f7;border-radius:4px 14px 14px 4px;padding:14px 16px;margin-bottom:14px}.message.human{border-color:var(--gold);background:#fff8e9}.message .who{font-weight:700;font-size:12px;margin-bottom:8px}.message .time{float:right;color:var(--muted);font-weight:400}.message pre{white-space:pre-wrap;word-break:break-word;font-family:inherit;line-height:1.6;margin:0;max-height:520px;overflow:auto}.attachment{margin-top:10px;padding:9px;background:white;border:1px dashed var(--line);border-radius:9px;font-size:12px}
.empty{padding:80px 30px;text-align:center;color:var(--muted)}.recovery{display:none;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:28px;box-shadow:var(--shadow)}.recovery.active{display:block}.recovery h2{font:700 25px Georgia,"Songti SC",serif}.recovery h3{margin-top:24px}.recovery li{margin:9px 0;line-height:1.6}.recovery pre{white-space:pre-wrap;background:#f1eee7;padding:15px;border-radius:12px;max-height:280px;overflow:auto}.nav{display:flex;gap:8px;margin-bottom:16px}.nav button{border:1px solid var(--green);background:white;color:var(--green);padding:9px 14px;border-radius:11px;cursor:pointer}.nav button.active{background:var(--green);color:white}
mark{background:#ffe294}.notice{font-size:12px;color:var(--muted);margin-top:14px}
@media(max-width:1000px){.cards{grid-template-columns:repeat(2,1fr)}.dashboard,.workspace{grid-template-columns:1fr}.sidebar{max-height:620px}.hero{flex-direction:column}.privacy{white-space:normal}}@media(max-width:620px){.shell{padding:14px}.cards{grid-template-columns:1fr}.filter-row{grid-template-columns:1fr}.hero h1{font-size:30px}}
</style>
</head>
<body>
<div class="shell">
  <div class="hero">
    <div><div class="eyebrow">PRIVATE · LOCAL · SEARCHABLE</div><h1>Claude Data Recovery</h1><p>把 Claude 数据导出变回可以搜索、筛选、阅读和继续使用的本地资料库。</p></div>
    <div class="privacy">🔒 单文件离线运行，不向网络上传数据</div>
  </div>
  <div class="cards" id="cards"></div>
  <div class="dashboard">
    <section class="panel"><h2>对话时间分布</h2><div class="month-bars" id="monthBars"></div></section>
    <section class="panel"><h2>主题分类</h2><div class="category-list" id="categoryList"></div></section>
  </div>
  <div class="nav"><button class="active" id="libraryTab">对话资料库</button><button id="recoveryTab">找回与申诉说明</button></div>
  <div id="libraryView" class="workspace">
    <aside class="sidebar">
      <div class="filters">
        <input class="search" id="search" placeholder="搜索标题、正文、附件内容…">
        <div class="filter-row"><select id="typeFilter"></select><select id="categoryFilter"></select><select id="priorityFilter"></select></div>
        <div class="results-meta" id="resultsMeta"></div>
      </div>
      <div class="list" id="list"></div>
    </aside>
    <main class="detail" id="detail"><div class="empty">从左侧选择一个对话。<br>也可以直接输入记得的关键词。</div></main>
  </div>
  <section class="recovery" id="recoveryView">
    <h2>最实际的找回路径</h2>
    <ol>
      <li><b>如账号被停用，可先申诉：</b>使用原账号登录 claude.ai 后进入官方申诉表。恢复原账号是唯一能原样恢复原聊天侧边栏的方式。</li>
      <li><b>完整历史无法导入新个人账号：</b>Anthropic 官方明确说明，数据导出不能导入另一个个人 Claude 账号，也不支持个人账号间迁移。</li>
      <li><b>恢复上下文：</b>在新账号中使用 Settings → Capabilities → Memory → Start import，粘贴下方记忆文本；官方提示该功能仍属实验性。</li>
      <li><b>继续具体项目：</b>从本页找到相关对话，点击“打开 Markdown”，把该文件上传到新 Claude 对话或项目中继续工作。</li>
    </ol>
    <div class="actions">
      <a class="btn" href="README_RECOVERY.md">打开完整恢复指南</a>
      <a class="btn secondary" href="memory_import.md">打开记忆导入文本</a>
      <button class="btn secondary" id="copyMemory">复制记忆文本</button>
    </div>
    <h3>账号记忆</h3>
    <pre id="memoryText"></pre>
    <h3>项目资料</h3>
    <pre id="projectText"></pre>
    <p class="notice">提示：本页里的第三方查看器仅作为备选。你的导出含账号资料、完整聊天和附件文本，优先使用当前离线版本。</p>
  </section>
</div>
<script type="application/json" id="dataset">__DATA__</script>
<script>
const data=JSON.parse(document.getElementById("dataset").textContent);
const chats=data.all_chats;
for(const chat of chats){
  chat.search_text=[
    chat.title,chat.summary,chat.first_prompt,
    ...chat.messages.flatMap(m=>[
      m.text,
      ...m.attachments.flatMap(a=>[a.file_name,a.extracted_content]),
      ...m.files.map(f=>f.file_name)
    ])
  ].filter(Boolean).join("\n").toLowerCase()
}
const nf=new Intl.NumberFormat("zh-CN");
const escapeHtml=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const shortDate=s=>s?String(s).slice(0,10):"未知";
const cards=[
  ["普通对话",nf.format(data.stats.conversation_count),"原 Claude 聊天"],
  ["全部消息",nf.format(data.stats.total_message_count),"含设计对话"],
  ["设计对话",nf.format(data.stats.design_chat_count),"独立设计记录"],
  ["附件与文件",nf.format(data.stats.attachment_count+data.stats.file_count),"可按文件名搜索"],
  ["时间跨度",data.stats.date_min.slice(0,10),`至 ${data.stats.date_max.slice(0,10)}`]
];
document.getElementById("cards").innerHTML=cards.map(x=>`<div class="card"><div class="label">${x[0]}</div><div class="value">${x[1]}</div><div class="sub">${x[2]}</div></div>`).join("");
const months=Object.entries(data.stats.month_counts).sort((a,b)=>a[0].localeCompare(b[0])); const maxMonth=Math.max(...months.map(x=>x[1]),1);
document.getElementById("monthBars").innerHTML=months.map(([m,n])=>`<div class="month"><b>${n}</b><div class="bar" style="height:${Math.max(5,n/maxMonth*85)}px" title="${m}: ${n}"></div><small>${m.slice(2)}</small></div>`).join("");
const cats=Object.entries(data.stats.category_counts).sort((a,b)=>b[1]-a[1]); const maxCat=Math.max(...cats.map(x=>x[1]),1);
document.getElementById("categoryList").innerHTML=cats.map(([c,n])=>`<div class="category-row"><span>${escapeHtml(c)}</span><div class="track"><i style="width:${n/maxCat*100}%"></i></div><b>${n}</b></div>`).join("");
const search=document.getElementById("search"), typeFilter=document.getElementById("typeFilter"), categoryFilter=document.getElementById("categoryFilter"), priorityFilter=document.getElementById("priorityFilter");
function options(first,values){return [`<option value="">${first}</option>`].concat(values.map(v=>`<option>${escapeHtml(v)}</option>`)).join("")}
typeFilter.innerHTML=options("全部类型",[...new Set(chats.map(x=>x.source_type))]);
categoryFilter.innerHTML=options("全部分类",[...new Set(chats.map(x=>x.category))].sort());
priorityFilter.innerHTML=options("全部优先级",["高","中","普通"]);
let current=null, filtered=[];
function matches(chat){
  const q=search.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return (!typeFilter.value||chat.source_type===typeFilter.value)&&(!categoryFilter.value||chat.category===categoryFilter.value)&&(!priorityFilter.value||chat.priority===priorityFilter.value)&&q.every(token=>chat.search_text.includes(token));
}
function renderList(){
  filtered=chats.filter(matches).sort((a,b)=>(b.updated_at||"").localeCompare(a.updated_at||""));
  document.getElementById("resultsMeta").textContent=`找到 ${filtered.length} / ${chats.length} 个对话`;
  document.getElementById("list").innerHTML=filtered.map(chat=>`<article class="item ${current===chat.uuid?"active":""}" data-id="${chat.uuid}"><h3>${escapeHtml(chat.title)}</h3><div class="meta"><span>${shortDate(chat.updated_at)}</span><span>${chat.message_count} 条消息</span><span>${nf.format(chat.char_count)} 字符</span></div><div class="tags"><span class="tag">${chat.source_type}</span><span class="tag">${chat.category}</span><span class="tag priority-${chat.priority}">${chat.priority}优先</span></div></article>`).join("");
  document.querySelectorAll(".item").forEach(el=>el.addEventListener("click",()=>selectChat(el.dataset.id)));
  if(!filtered.some(chat=>chat.uuid===current)){
    if(filtered[0]){current=filtered[0].uuid;location.hash=encodeURIComponent(current);renderDetail(filtered[0])}
    else{current=null;document.getElementById("detail").innerHTML='<div class="empty">没有符合条件的对话。<br>试试缩短关键词或清除筛选。</div>'}
  }
}
function messageHtml(m){
  const attachmentHtml=m.attachments.map(a=>`<div class="attachment">📎 ${escapeHtml(a.file_name||"未命名附件")} · ${escapeHtml(a.file_type||"未知类型")} · ${nf.format(a.file_size||0)} bytes${a.extracted_content?`<details><summary>查看附件提取内容</summary><pre>${escapeHtml(a.extracted_content)}</pre></details>`:""}</div>`).join("");
  const fileHtml=m.files.map(f=>`<div class="attachment">📄 ${escapeHtml(f.file_name||"未命名文件")} · ${escapeHtml(f.file_uuid)}</div>`).join("");
  return `<article class="message ${["human","user"].includes(m.sender)?"human":"assistant"}"><div class="who">${escapeHtml(m.sender_label)}<span class="time">${escapeHtml(shortDate(m.created_at))} · ${escapeHtml(m.types.join(", "))}</span></div><pre>${escapeHtml(m.text||"（空消息）")}</pre>${attachmentHtml}${fileHtml}</article>`
}
function renderDetail(chat){
  document.getElementById("detail").innerHTML=`<div class="detail-head"><h2>${escapeHtml(chat.title)}</h2><div class="meta"><span>${escapeHtml(chat.source_type)}</span><span>${escapeHtml(chat.category)}</span><span>${shortDate(chat.created_at)} → ${shortDate(chat.updated_at)}</span><span>${chat.message_count} 条消息</span><span>UUID ${escapeHtml(chat.uuid)}</span></div><div class="actions"><a class="btn" href="${encodeURI(chat.markdown_file)}">打开 Markdown</a><button class="btn secondary" id="copyLink">复制 UUID</button></div></div><div class="messages">${chat.summary?`<article class="message"><div class="who">原始摘要</div><pre>${escapeHtml(chat.summary)}</pre></article>`:""}${chat.messages.map(messageHtml).join("")}</div>`;
  document.getElementById("copyLink").onclick=()=>copyText(chat.uuid);
}
function selectChat(id){
  const chat=chats.find(x=>x.uuid===id); if(!chat)return; current=id; location.hash=encodeURIComponent(id); renderList(); renderDetail(chat);
}
function copyText(text){if(navigator.clipboard&&location.protocol!=="file:"){navigator.clipboard.writeText(text)}else{const t=document.createElement("textarea");t.value=text;document.body.appendChild(t);t.select();document.execCommand("copy");t.remove()}}
[search,typeFilter,categoryFilter,priorityFilter].forEach(el=>el.addEventListener(el===search?"input":"change",renderList));
document.getElementById("memoryText").textContent=data.memory_import_text||"（无记忆数据）";
document.getElementById("projectText").textContent=data.project_recovery_text||"（无项目数据）";
document.getElementById("copyMemory").onclick=()=>copyText(data.memory_import_text||"");
const libraryTab=document.getElementById("libraryTab"), recoveryTab=document.getElementById("recoveryTab"), libraryView=document.getElementById("libraryView"), recoveryView=document.getElementById("recoveryView");
libraryTab.onclick=()=>{libraryTab.classList.add("active");recoveryTab.classList.remove("active");libraryView.style.display="grid";recoveryView.classList.remove("active")};
recoveryTab.onclick=()=>{recoveryTab.classList.add("active");libraryTab.classList.remove("active");libraryView.style.display="none";recoveryView.classList.add("active")};
renderList(); const hash=decodeURIComponent(location.hash.slice(1)); if(hash&&chats.some(x=>x.uuid===hash))selectChat(hash); else if(filtered[0])selectChat(filtered[0].uuid);
</script>
</body></html>"""
    return template.replace("__DATA__", safe_data)


def project_to_text(projects: list[dict[str, Any]]) -> str:
    if not projects:
        return "没有项目数据。"
    sections: list[str] = []
    for project in projects:
        sections.extend(
            [
                f"项目：{clean_text(project.get('name') or '未命名项目')}",
                f"UUID：{clean_text(project.get('uuid'))}",
                f"描述：{clean_text(project.get('description'))}",
                f"是否私密：{project.get('is_private')}",
                f"创建时间：{clean_text(project.get('created_at'))}",
                f"最后更新：{clean_text(project.get('updated_at'))}",
                "",
                "项目提示词：",
                clean_text(project.get("prompt_template")),
                "",
                "文档数：" + str(len(project.get("docs") or [])),
                "",
            ]
        )
    return "\n".join(sections).strip()


def memory_value_to_text(value: Any, heading_level: int = 2) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = clean_text(value).strip()
        if text.startswith(("{", "[", '"')):
            try:
                parsed = json.loads(text)
                if parsed != value:
                    return memory_value_to_text(parsed, heading_level)
            except json.JSONDecodeError:
                pass
        return text.replace("\\n", "\n").replace('\\"', '"')
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            parts.extend(
                [
                    f"{'#' * min(heading_level, 6)} {clean_text(key)}",
                    "",
                    memory_value_to_text(item, heading_level + 1),
                    "",
                ]
            )
        return "\n".join(parts).strip()
    if isinstance(value, list):
        return "\n\n".join(memory_value_to_text(item, heading_level) for item in value if item is not None)
    return clean_text(value)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(clean_text(content), encoding="utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="claude-data-recovery",
        description="Build a private, offline viewer and Markdown archive from a Claude data export.",
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Extracted Claude export directory, or its conversations.json file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("claude-recovery-output"),
        help="Output directory (default: ./claude-recovery-output).",
    )
    parser.add_argument("--version", action="version", version="claude-data-recovery 0.1.0")
    args = parser.parse_args()
    source_input = args.source.resolve()
    source = source_input.parent if source_input.is_file() else source_input
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    markdown_dir = output / "markdown"
    markdown_dir.mkdir(exist_ok=True)

    conversations_path = source_input if source_input.is_file() else source / "conversations.json"
    if not conversations_path.is_file():
        parser.error(f"Could not find conversations.json at: {conversations_path}")
    raw_conversations = safe_json_load(conversations_path)
    if not isinstance(raw_conversations, list):
        parser.error("conversations.json must contain a JSON array.")
    conversations = [
        normalize_conversation(raw, ordinal)
        for ordinal, raw in enumerate(raw_conversations, 1)
        if isinstance(raw, dict)
    ]

    design_chats: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for ordinal, path in enumerate(sorted((source / "design_chats").glob("*.json")), 1):
        raw = safe_json_load(path)
        surrogate_count = count_surrogates(raw)
        if surrogate_count:
            warnings.append(
                {
                    "file": str(path.relative_to(source)),
                    "issue": f"发现 {surrogate_count} 个不成对 Unicode 代理字符",
                    "action": "整理副本中替换为 Unicode U+FFFD 占位符；原文件保持不变",
                }
            )
        if isinstance(raw, dict):
            design_chats.append(normalize_design_chat(raw, ordinal))

    projects = [safe_json_load(path) for path in sorted((source / "projects").glob("*.json"))]
    projects = [project for project in projects if isinstance(project, dict)]
    users_raw = safe_json_load(source / "users.json") if (source / "users.json").exists() else []
    users = users_raw if isinstance(users_raw, list) else [users_raw]
    memories_raw = safe_json_load(source / "memories.json") if (source / "memories.json").exists() else []
    memories = memories_raw if isinstance(memories_raw, list) else [memories_raw]

    for chat in conversations + design_chats:
        write_text(output / chat["markdown_file"], markdown_for_chat(chat))

    conversations_memory = "\n\n".join(
        clean_text(item.get("conversations_memory"))
        for item in memories
        if isinstance(item, dict) and item.get("conversations_memory")
    ).strip()
    project_memories = [
        item.get("project_memories")
        for item in memories
        if isinstance(item, dict) and item.get("project_memories")
    ]
    project_memory_text = memory_value_to_text(project_memories)
    memory_import_text = conversations_memory
    if project_memory_text and project_memory_text not in ("[]", "{}"):
        memory_import_text += "\n\n# Project memories\n" + project_memory_text

    all_chats = conversations + design_chats
    for chat in all_chats:
        chat.pop("_search_text", None)

    date_values = [chat["created_at"] for chat in all_chats if chat["created_at"]]
    stats = {
        "conversation_count": len(conversations),
        "design_chat_count": len(design_chats),
        "total_chat_count": len(all_chats),
        "conversation_message_count": sum(chat["message_count"] for chat in conversations),
        "design_message_count": sum(chat["message_count"] for chat in design_chats),
        "total_message_count": sum(chat["message_count"] for chat in all_chats),
        "attachment_count": sum(chat["attachment_count"] for chat in all_chats),
        "file_count": sum(chat["file_count"] for chat in all_chats),
        "total_char_count": sum(chat["char_count"] for chat in all_chats),
        "project_count": len(projects),
        "memory_record_count": len(memories),
        "date_min": min(date_values) if date_values else "",
        "date_max": max(chat["updated_at"] or chat["created_at"] for chat in all_chats) if all_chats else "",
        "month_counts": dict(
            sorted(collections.Counter(chat["month"] for chat in conversations).items())
        ),
        "category_counts": dict(
            sorted(collections.Counter(chat["category"] for chat in conversations).items())
        ),
        "priority_counts": dict(
            sorted(collections.Counter(chat["priority"] for chat in conversations).items())
        ),
    }
    source_files = []
    for path in sorted(source.rglob("*")):
        if path.is_file() and path.name != ".DS_Store":
            source_files.append(
                {
                    "file": str(path.relative_to(source)),
                    "size_bytes": path.stat().st_size,
                }
            )
    dataset = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_path": str(source),
        "stats": stats,
        "conversations": conversations,
        "design_chats": design_chats,
        "users": users,
        "memories": memories,
        "projects": projects,
        "memory_import_text": memory_import_text,
        "project_recovery_text": project_to_text(projects),
        "warnings": warnings,
        "source_files": source_files,
        "sources": [
            {"name": "Claude 官方申诉说明", "url": OFFICIAL_APPEAL},
            {"name": "Claude 官方数据导出/迁移说明", "url": OFFICIAL_EXPORT},
            {"name": "Claude 官方记忆导入说明", "url": OFFICIAL_MEMORY},
            {"name": "Claude AI Export Renderer（开源备选）", "url": CLAUDE_RENDERER},
            {"name": "LLM Conversations Viewer（开源备选）", "url": LOCAL_VIEWER},
        ],
    }

    normalized_path = output / "normalized_data.json"
    normalized_path.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    html_dataset = {
        "stats": stats,
        "all_chats": all_chats,
        "memory_import_text": memory_import_text,
        "project_recovery_text": dataset["project_recovery_text"],
        "sources": dataset["sources"],
    }
    write_text(output / "index.html", build_html(html_dataset))
    write_text(output / "memory_import.md", memory_import_text or "没有可导入的记忆文本。")
    write_text(output / "project_recovery.md", "# Claude 项目恢复资料\n\n" + dataset["project_recovery_text"])

    user = users[0] if users and isinstance(users[0], dict) else {}
    account_md = "\n".join(
        [
            "# 账号与申诉资料",
            "",
            f"- 姓名：{clean_text(user.get('full_name'))}",
            f"- 邮箱：{clean_text(user.get('email_address'))}",
            f"- 已验证手机号：{clean_text(user.get('verified_phone_number'))}",
            f"- 账号 UUID：{clean_text(user.get('uuid'))}",
            f"- 数据范围：{stats['date_min'][:10]} 至 {stats['date_max'][:10]}",
            f"- 普通对话：{stats['conversation_count']} 个",
            f"- 普通消息：{stats['conversation_message_count']} 条",
            "",
            "## 建议的申诉材料",
            "",
            "1. 说明登录邮箱、账号 UUID 和大致被封时间。",
            "2. 简洁描述日常用途，明确请求人工复核。",
            "3. 若怀疑异地登录或账号被盗，写明时间、地区和采取过的安全措施。",
            "4. 不要重复提交大量申诉；保留提交日期和回复邮件。",
            "",
            "## 英文申诉模板",
            "",
            "Subject: Request for manual review of suspended Claude account",
            "",
            "Hello Anthropic Safeguards Team,",
            "",
            f"My Claude account associated with {clean_text(user.get('email_address'))} was suspended. "
            "I believe this may have been an error and would appreciate a manual review. "
            "I primarily used Claude for legitimate work and personal productivity. "
            "Please let me know if you need any additional information to verify the account or clarify its usage.",
            "",
            "Thank you.",
            "",
            f"官方说明：{OFFICIAL_APPEAL}",
            "",
        ]
    )
    write_text(output / "account_appeal.md", account_md)

    warning_text = "\n".join(
        f"- `{item['file']}`：{item['issue']}；{item['action']}" for item in warnings
    ) or "- 未发现阻断性数据问题。"
    readme = f"""# Claude 数据恢复包

这是一份从原始 Claude 数据导出生成的本地恢复包。原始文件没有被修改。

## 从这里开始

1. 打开 `index.html`：按标题、正文、附件内容、分类和优先级搜索。
2. 找到需要继续的对话后，进入 `markdown/`，把对应 Markdown 文件上传到新的 Claude 对话或项目。
3. 新账号可在 Settings → Capabilities → Memory → Start import 中粘贴 `memory_import.md`。
4. 若要恢复原账号，参考 `account_appeal.md` 并走官方申诉。

## 重要结论

- Anthropic 官方明确说明：导出的数据不能导入另一个个人 Claude 账号，也不支持个人账号之间迁移。
- 记忆文本可以通过官方 Memory Import 流程导入，但该功能仍属实验性。
- 若原账号恢复，原聊天侧边栏是否恢复取决于 Anthropic 的账号恢复结果；本工具不会写入或更改 Claude 云端。

## 数据概览

- 普通对话：{stats['conversation_count']} 个
- 普通消息：{stats['conversation_message_count']} 条
- 设计对话：{stats['design_chat_count']} 个，消息 {stats['design_message_count']} 条
- 时间范围：{stats['date_min'][:10]} 至 {stats['date_max'][:10]}
- 附件：{stats['attachment_count']} 个；文件引用：{stats['file_count']} 个
- 项目：{stats['project_count']} 个；记忆记录：{stats['memory_record_count']} 组

## 数据质量

{warning_text}

## 官方与备选方案

- [Claude 官方申诉说明]({OFFICIAL_APPEAL})
- [Claude 官方数据导出与迁移限制]({OFFICIAL_EXPORT})
- [Claude 官方记忆导入说明]({OFFICIAL_MEMORY})
- [Claude AI Export Renderer（MIT，单 HTML，直接选择 conversations.json）]({CLAUDE_RENDERER})
- [LLM Conversations Viewer（MIT，支持 Claude/ChatGPT/Z.ai 的 JSON 或 ZIP）]({LOCAL_VIEWER})

隐私建议：这份导出包含完整聊天、附件提取文本和账号资料。除非你充分信任第三方服务，否则优先使用本恢复包的离线 HTML。
"""
    write_text(output / "README_RECOVERY.md", readme)
    print(json.dumps({"output": str(output), "stats": stats, "warnings": warnings}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

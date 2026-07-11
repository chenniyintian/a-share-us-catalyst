from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Optional, Union

import requests


def load_env(path: Union[str, Path] = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def send_telegram(markdown: str, *, token: Optional[str] = None, chat_id: Optional[str] = None) -> dict[str, Any]:
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("缺少 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID")
    text = _telegram_excerpt(markdown)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True}, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _telegram_excerpt(markdown: str, max_len: int = 3800) -> str:
    text = markdown.replace("|", " ")
    if len(text) <= max_len:
        return text
    return text[: max_len - 40].rstrip() + "\n\n[已截断，完整报告见本地 reports 目录]"


def send_email(
    markdown: str,
    *,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
    to: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    """Send the report via SMTP email.

    SMTP config is read from env vars with fallback to provided args:
      SMTP_HOST    — default smtp.qq.com
      SMTP_PORT    — default 587
      SMTP_USER    — your email address
      SMTP_PASSWORD — SMTP authorization code (not login password)
      EMAIL_TO     — recipient(s), comma-separated
    """
    host = smtp_host or os.environ.get("SMTP_HOST", "smtp.qq.com")
    port = smtp_port or int(os.environ.get("SMTP_PORT", "587"))
    user = smtp_user or os.environ.get("SMTP_USER")
    password = smtp_password or os.environ.get("SMTP_PASSWORD")
    recipients = to or os.environ.get("EMAIL_TO")

    if not user or not password or not recipients:
        raise RuntimeError("缺少 SMTP_USER / SMTP_PASSWORD / EMAIL_TO 配置")

    addr_list = [a.strip() for a in recipients.split(",") if a.strip()]
    if not addr_list:
        raise RuntimeError("EMAIL_TO 为空")

    title = subject or os.environ.get("EMAIL_SUBJECT", "美股映射A股早报")

    # Build HTML body from markdown (simple conversion)
    html_body = _markdown_to_html_email(markdown)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = title
    msg["From"] = user
    msg["To"] = ", ".join(addr_list)

    msg.attach(MIMEText(markdown, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        server = smtplib.SMTP(host, port, timeout=30)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(user, password)
        server.sendmail(user, addr_list, msg.as_string())
        server.quit()
    except Exception as exc:
        raise RuntimeError(f"邮件发送失败: {exc}") from exc

    return {"ok": True, "to": addr_list, "subject": title}


def _markdown_to_html_email(md: str) -> str:
    """Convert markdown report to a readable HTML email."""
    import re

    lines = md.split("\n")
    html_lines = []
    in_table = False
    in_code = False

    # Inline: bold, remove excessive symbols
    def inline(text: str) -> str:
        # bold
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        # avoid raw HTML
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return text

    for line in lines:
        stripped = line.strip()

        # code block toggle
        if stripped.startswith("```"):
            in_code = not in_code
            continue

        if in_code:
            html_lines.append(f'<pre style="background:#f5f5f5;padding:8px;font-size:12px;">{inline(line)}</pre>')
            continue

        # blank line
        if not stripped:
            if in_table:
                html_lines.append("</table>")
                in_table = False
            continue

        # heading
        if stripped.startswith("# "):
            if in_table:
                html_lines.append("</table>")
                in_table = False
            html_lines.append(f'<h2 style="color:#1a1a1a;border-bottom:1px solid #eee;padding-bottom:4px;">{inline(stripped[2:])}</h2>')
        elif stripped.startswith("## "):
            if in_table:
                html_lines.append("</table>")
                in_table = False
            html_lines.append(f'<h3 style="color:#333;">{inline(stripped[3:])}</h3>')
        elif stripped.startswith("### "):
            if in_table:
                html_lines.append("</table>")
                in_table = False
            html_lines.append(f'<h4 style="color:#555;">{inline(stripped[4:])}</h4>')
        # table row
        elif stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            if all(c.startswith("---") or c == "---" or c == ":---" for c in cells):
                # separator row, skip
                continue
            if not in_table:
                html_lines.append('<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-size:13px;width:100%;">')
                in_table = True
                html_lines.append("<thead>")
                html_lines.append("<tr>" + "".join(f'<th style="background:#f0f0f0;">{inline(c)}</th>' for c in cells) + "</tr>")
                html_lines.append("</thead><tbody>")
            else:
                html_lines.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
        # horizontal rule
        elif stripped == "---":
            html_lines.append("<hr>")
        # blockquote
        elif stripped.startswith("> "):
            html_lines.append(f'<blockquote style="color:#666;border-left:3px solid #ccc;padding-left:8px;margin:8px 0;">{inline(stripped[2:])}</blockquote>')
        # list item
        elif stripped.startswith("- "):
            html_lines.append(f'<li>{inline(stripped[2:])}</li>')
        # plain paragraph
        else:
            if in_table:
                html_lines.append("</table>")
                in_table = False
            html_lines.append(f'<p style="margin:4px 0;">{inline(line)}</p>')

    if in_table:
        html_lines.append("</table>")

    body = "\n".join(html_lines)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:'Microsoft YaHei','PingFang SC',Arial,sans-serif;max-width:720px;margin:0 auto;color:#333;">
{body}
<hr>
<p style="color:#999;font-size:11px;">本邮件由九点猫研 CatDesk 9 自动生成，内容仅为研究参考，不构成投资建议。</p>
</body>
</html>"""

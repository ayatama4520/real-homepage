#!/usr/bin/env python3
"""Turn plain-text drafts in drafts/*.txt into fully wired post pages.

Draft file format:

    Title: 記事のタイトル
    Tags: エッセイ, 自己紹介, 猫
    Date: 2026-04-01        (optional, defaults to today JST)
    ---
    本文1段落目。

    本文2段落目。1行の途中で改行すると<br>になる。

    ***

    シーンブレークの後の段落。
"""
import glob
import os
import re
import shutil
from datetime import datetime, timedelta, timezone

SITE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(SITE_ROOT, "posts")
DRAFTS_DIR = os.path.join(SITE_ROOT, "drafts")
PUBLISHED_DIR = os.path.join(DRAFTS_DIR, "published")
TOP_INDEX = os.path.join(SITE_ROOT, "index.html")
POSTS_INDEX = os.path.join(POSTS_DIR, "index.html")

JST = timezone(timedelta(hours=9))

POST_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - リアルホームページ</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>

<h1 class="site-title">リアルホームページ</h1>

<div class="menu">
  <a href="../index.html">トップ</a><span class="sep">|</span><a href="../index.html#profile">プロフィール</a><span class="sep">|</span><a href="index.html">記事一覧</a><span class="sep">|</span><a href="../index.html#contact">連絡先</a>
</div>

<hr>

<h2>{title}</h2>
<p class="post-meta">{date_dotted} 公開</p>
<p class="post-tags">{tags_line}</p>

{body_html}

<hr>

<div class="post-nav">
  <span class="prev">{prev_link}</span>
  <span class="next">{next_link}</span>
</div>

<p><a href="index.html">記事一覧に戻る</a> ／ <a href="../index.html">トップに戻る</a></p>

<footer>
  <p>Copyright (C) 2026 玉岡礼汰 All Rights Reserved.</p>
</footer>

</body>
</html>
"""


def parse_draft(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if "---" not in content:
        raise ValueError(f"{path}: missing '---' line between header and body")
    header, body = content.split("---", 1)
    fields = {}
    for line in header.strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip()
    title = fields.get("title", "").strip()
    if not title:
        raise ValueError(f"{path}: missing 'Title:' line")
    tags = [t.strip() for t in fields.get("tags", "").split(",") if t.strip()]
    date_str = fields.get("date", "").strip() or datetime.now(JST).date().isoformat()
    return title, tags, date_str, body.strip()


def body_to_html(body):
    blocks = re.split(r"\n\s*\n", body.strip())
    html_blocks = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block == "***":
            html_blocks.append('<p class="scene-break">＊　＊　＊</p>')
        else:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            html_blocks.append("<p>" + "<br>\n".join(lines) + "</p>")
    return "\n\n".join(html_blocks)


def next_post_number():
    nums = []
    for path in glob.glob(os.path.join(POSTS_DIR, "post-*.html")):
        m = re.search(r"post-(\d+)\.html$", path)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def load(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def save(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def update_prev_post_next_link(prev_num, new_num, new_title):
    prev_path = os.path.join(POSTS_DIR, f"post-{prev_num:03d}.html")
    content = load(prev_path)
    new_link = f'<a href="post-{new_num:03d}.html">次の記事: {new_title} &gt;&gt;</a>'
    updated = content.replace(
        '<span class="next"></span>', f'<span class="next">{new_link}</span>'
    )
    if updated == content:
        raise RuntimeError(
            f"{prev_path}: could not find an empty <span class=\"next\"></span> to update "
            "(is this really the most recent post?)"
        )
    save(prev_path, updated)


def build_li(date_dotted, href, title, is_new):
    tag = '<span class="new-tag">New!</span>' if is_new else ""
    return (
        f'  <li>\n'
        f'    {tag}<span class="post-date">{date_dotted}</span>\n'
        f'    <a href="{href}">{title}</a>\n'
        f'  </li>'
    )


def update_list_page(path, date_dotted, href, title, limit=None):
    content = load(path)
    m = re.search(r'(<ul class="post-list">\n)(.*?)(\n</ul>)', content, re.S)
    if not m:
        raise RuntimeError(f'{path}: could not find <ul class="post-list">')
    existing_block = m.group(2)
    existing_lis = re.findall(r"  <li>.*?</li>", existing_block, re.S)
    existing_lis = [
        li.replace('<span class="new-tag">New!</span>', "") for li in existing_lis
    ]
    new_li = build_li(date_dotted, href, title, is_new=True)
    all_lis = [new_li] + existing_lis
    if limit is not None:
        all_lis = all_lis[:limit]
    new_block = "\n".join(all_lis)
    new_content = (
        content[: m.start()] + m.group(1) + new_block + m.group(3) + content[m.end():]
    )
    save(path, new_content)


def main():
    os.makedirs(PUBLISHED_DIR, exist_ok=True)
    draft_paths = sorted(
        p
        for p in glob.glob(os.path.join(DRAFTS_DIR, "*.txt"))
        if os.path.basename(p).lower() != "readme.txt"
    )
    if not draft_paths:
        print("No drafts to publish.")
        return

    for draft_path in draft_paths:
        title, tags, date_str, body = parse_draft(draft_path)
        y, mo, d = date_str.split("-")
        date_dotted = f"{y}.{mo}.{d}"

        new_num = next_post_number()
        prev_num = new_num - 1

        tags_line = " ".join(f"#{t}" for t in tags)
        body_html = body_to_html(body)

        prev_link = ""
        prev_path = os.path.join(POSTS_DIR, f"post-{prev_num:03d}.html")
        if prev_num >= 1 and os.path.exists(prev_path):
            prev_content = load(prev_path)
            prev_title_m = re.search(r"<h2>(.*?)</h2>", prev_content, re.S)
            prev_title = prev_title_m.group(1).strip() if prev_title_m else ""
            prev_link = (
                f'<a href="post-{prev_num:03d}.html">&lt;&lt; 前の記事: {prev_title}</a>'
            )
            update_prev_post_next_link(prev_num, new_num, title)

        new_post_html = POST_TEMPLATE.format(
            title=title,
            date_dotted=date_dotted,
            tags_line=tags_line,
            body_html=body_html,
            prev_link=prev_link,
            next_link="",
        )
        new_post_path = os.path.join(POSTS_DIR, f"post-{new_num:03d}.html")
        save(new_post_path, new_post_html)

        update_list_page(
            POSTS_INDEX, date_dotted, f"post-{new_num:03d}.html", title, limit=None
        )
        update_list_page(
            TOP_INDEX, date_dotted, f"posts/post-{new_num:03d}.html", title, limit=3
        )

        shutil.move(
            draft_path, os.path.join(PUBLISHED_DIR, os.path.basename(draft_path))
        )
        print(f"Published {draft_path} as post-{new_num:03d}.html ({title!r})")


if __name__ == "__main__":
    main()

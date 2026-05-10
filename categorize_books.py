#!/usr/bin/env python3
"""
Chinese Book Categorizer
Scores .txt files (UTF-8) by keyword frequency and sorts them into folders.
Usage: python3 categorize_books.py [--dir /path/to/books] [--sample 5000] [--copy]
"""

import os
import re
import shutil
import argparse
from pathlib import Path
from collections import defaultdict

# ─────────────────────────────────────────────
#  CATEGORY DEFINITIONS  (edit freely)
# ─────────────────────────────────────────────
CATEGORIES = {
    "言情_Romance": [
        "爱情", "恋爱", "相思", "情人", "心动", "暗恋", "表白", "初恋",
        "温柔", "深情", "痴情", "爱慕", "情侣", "求婚", "婚姻", "嫁",
        "甜蜜", "吻", "拥抱", "心跳", "情书", "一见钟情", "缘分", "爱意",
        "情感", "爱人", "心上人", "浪漫", "柔情", "思念",
    ],
    "悬疑_Thriller": [
        "谋杀", "凶手", "侦探", "推理", "线索", "嫌疑", "案件", "犯罪",
        "警察", "证据", "真相", "密室", "尸体", "失踪", "秘密", "追查",
        "悬案", "罪行", "凶案", "刑警", "破案", "阴谋", "暗杀", "监控",
        "指纹", "审讯", "通缉", "越狱", "绑架", "勒索",
    ],
    "玄幻_Fantasy": [
        "修炼", "灵气", "仙", "魔", "法术", "神功", "丹药", "宗门",
        "武功", "剑法", "内力", "境界", "修为", "妖兽", "法宝", "灵根",
        "飞升", "渡劫", "灵魂", "异界", "元神", "功法", "结丹", "筑基",
        "神器", "妖族", "仙界", "魔道", "九天", "洪荒",
    ],
    "历史_Historical": [
        "朝代", "皇帝", "皇宫", "大臣", "将军", "王朝", "史记", "太子",
        "皇后", "宫廷", "征战", "诸侯", "变法", "科举", "官员", "古代",
        "封建", "宰相", "太后", "藩王", "圣旨", "朝廷", "战役", "历史",
        "帝国", "王位", "臣子", "封地", "奏折", "禁军",
    ],
    "科幻_SciFi": [
        "星际", "宇宙", "飞船", "机器人", "人工智能", "太空", "星球",
        "科技", "未来", "外星", "基因", "克隆", "量子", "虚拟现实",
        "赛博", "纳米", "时空", "穿越时间", "维度", "光速", "星系",
        "文明", "进化", "数据", "程序", "算法", "超级计算机", "核聚变",
        "反物质", "黑洞",
    ],
    "武侠_Wuxia": [
        "江湖", "武林", "侠客", "剑客", "门派", "武功", "轻功", "暗器",
        "镖局", "帮派", "武当", "少林", "刀法", "掌法", "内功", "秘籍",
        "恩仇", "侠义", "行走江湖", "仇人", "仗剑", "快意恩仇", "绿林",
        "盟主", "武器", "拳脚", "比武", "切磋", "隐士", "大侠",
    ],
    "都市_Urban": [
        "都市", "城市", "公司", "职场", "白领", "上班", "老板", "同事",
        "创业", "商业", "股票", "房子", "租房", "地铁", "购物", "网络",
        "手机", "微信", "社交", "现代", "北京", "上海", "广州", "深圳",
        "互联网", "电商", "资本", "投资", "办公室", "项目",
    ],
    "恐怖_Horror": [
        "鬼", "灵异", "阴间", "诅咒", "恐怖", "惊吓", "幽灵", "阴魂",
        "邪灵", "阴森", "恐惧", "血腥", "尸", "墓地", "地狱", "黑暗",
        "噩梦", "怪异", "灵魂", "冤魂", "厉鬼", "阴气", "闹鬼", "神秘",
        "超自然", "降头", "邪术", "吸血鬼", "僵尸", "鬼屋",
    ],
    "青春_YouthCampus": [
        "校园", "学校", "同学", "高考", "大学", "青春", "毕业", "老师",
        "班级", "学生", "课堂", "宿舍", "社团", "军训", "青涩", "初中",
        "高中", "暗恋", "友情", "成长", "懵懂", "操场", "图书馆", "考试",
        "作业", "奖学金", "留学", "毕业典礼", "同窗", "记忆",
    ],
    "古典文学_ClassicLit": [
        "诗", "词", "赋", "文言", "君子", "仁义", "道德", "礼仪",
        "经典", "儒家", "道家", "论语", "孟子", "四书", "五经", "子曰",
        "古文", "典故", "传记", "列传", "本纪", "志怪", "笔记", "杂记",
        "散文", "骈文", "古诗", "唐诗", "宋词", "元曲",
    ],
}

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def read_sample(filepath: Path, max_chars: int) -> str:
    """Read up to max_chars from beginning + middle + end of file."""
    try:
        size = filepath.stat().st_size
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            if size <= max_chars:
                return f.read()
            third = max_chars // 3
            start = f.read(third)
            f.seek(max(0, size // 2 - third // 2))
            middle = f.read(third)
            f.seek(max(0, size - third))
            end = f.read(third)
            return start + middle + end
    except Exception as e:
        print(f"  [WARN] Cannot read {filepath.name}: {e}")
        return ""


def score_text(text: str) -> dict[str, int]:
    """Return raw keyword hit counts per category."""
    scores: dict[str, int] = defaultdict(int)
    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            scores[category] += text.count(kw)
    return scores


def best_category(scores: dict[str, int]) -> str:
    """Return the top category, or 'other' if all scores are zero."""
    if not scores or max(scores.values()) == 0:
        return "其他_Other"
    return max(scores, key=lambda c: scores[c])


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Categorize Chinese .txt books into folders.")
    parser.add_argument("--dir",    default=".", help="Directory containing .txt files (default: current dir)")
    parser.add_argument("--out",    default=None, help="Output base directory (default: same as --dir)")
    parser.add_argument("--sample", type=int, default=100000, help="Chars to sample per file (default: 5000)")
    parser.add_argument("--copy",   action="store_true", help="Copy files instead of moving them")
    args = parser.parse_args()

    src_dir = Path(args.dir).resolve()
    out_dir = Path(args.out).resolve() if args.out else src_dir
    action  = "Copying" if args.copy else "Moving"

    txt_files = sorted(src_dir.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {src_dir}")
        return

    print(f"Found {len(txt_files)} .txt file(s) in {src_dir}")
    print(f"Sampling up to {args.sample} chars per file\n")

    stats: dict[str, list[str]] = defaultdict(list)

    for filepath in txt_files:
        text   = read_sample(filepath, args.sample)
        scores = score_text(text)
        cat    = best_category(scores)
        total  = sum(scores.values())

        # Build a short score summary for display
        top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        score_str = ", ".join(f"{c.split('_')[1]}:{v}" for c, v in top if v > 0) or "no hits"

        print(f"  {filepath.name}")
        print(f"    → {cat}  (total hits: {total}  |  top: {score_str})")

        # Create destination folder and move/copy
        dest_folder = out_dir / cat
        dest_folder.mkdir(parents=True, exist_ok=True)
        dest_path = dest_folder / filepath.name

        if args.copy:
            shutil.copy2(filepath, dest_path)
        else:
            shutil.move(str(filepath), dest_path)

        stats[cat].append(filepath.name)

    # ── Summary ────────────────────────────────
    print("\n" + "─" * 50)
    print("SUMMARY")
    print("─" * 50)
    for cat in sorted(stats):
        label = cat.split("_", 1)[-1]   # English part
        print(f"  {label:20s} → {len(stats[cat])} file(s)")
    print(f"\n{action} complete. Files are in: {out_dir}")


if __name__ == "__main__":
    main()

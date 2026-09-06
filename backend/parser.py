import re
from command_db import COMMAND_DB, levenshtein_distance


def _spell_check_command(line, threshold=2):
    """
    拼写检查：对未匹配的命令，在知识库中寻找最接近的正确命令
    返回: None 或 {"original": "...", "suggestion": "...", "distance": N}
    """
    if not line or len(line) < 2:
        return None

    line_lower = line.lower().strip()
    best_match = None
    best_dist = threshold + 1
    input_base = line_lower.split()[0] if line_lower.split() else line_lower

    candidates = set()
    for cmd_key in COMMAND_DB:
        candidates.add(cmd_key.lower())
        candidates.add(cmd_key.lower().split()[0])

    for cmd_base in candidates:
        if cmd_base == line_lower:
            continue
        compare = input_base if len(line_lower.split()) > 1 else line_lower
        target = cmd_base.split()[0] if len(line_lower.split()) > 1 else cmd_base
        dist = levenshtein_distance(compare, target)
        if dist > 0 and dist < best_dist:
            best_dist = dist
            best_match = target

    # 再检查是否是命令前缀不完整（如输入 "int" 应该是 "interface"）
    if best_dist > threshold:
        parts = line_lower.split()
        if parts:
            prefix = parts[0]
            for cmd_key in COMMAND_DB:
                cmd_base = cmd_key.split()[0]
                if cmd_base.startswith(prefix) and len(cmd_base) > len(prefix) and len(prefix) >= 2:
                    return {
                        "original": parts[0],
                        "suggestion": cmd_base,
                        "distance": len(cmd_base) - len(prefix),
                        "hint": f"可能是命令前缀不完整，建议输入: {cmd_base}"
                    }

    if best_match and best_dist <= threshold:
        return {
            "original": line_lower,
            "suggestion": best_match,
            "distance": best_dist,
            "hint": f"是否想输入: {best_match}？"
        }

    return None


def parse_config(config: str):
    """
    解析 H3C 配置字符串，逐行匹配命令知识库。
    同时检测拼写错误。
    返回: {
        "parsed": [...],
        "spelling_errors": [...],  # 拼写错误列表
        "unmatched": [...],        # 未匹配的命令列表
    }
    """
    parsed = []
    spelling_errors = []
    unmatched = []

    for raw_line in config.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        matched = None
        for command, info in sorted(COMMAND_DB.items(), key=lambda x: len(x[0]), reverse=True):
            if line == command or line.startswith(command + " "):
                matched = {
                    "command": line,
                    "title": info.get("title", ""),
                    "explanation": info.get("explanation", ""),
                    "category": info.get("category", "其他"),
                    "knowledge": info.get("knowledge", ""),
                    "scenario": info.get("scenario", ""),
                    "related_commands": info.get("related_commands", []),
                    "common_errors": info.get("common_errors", []),
                    "troubleshooting": info.get("troubleshooting", ""),
                }
                break

        if matched:
            parsed.append(matched)
        else:
            # 拼写检查
            spell = _spell_check_command(line)
            entry = {
                "command": line,
                "title": "暂未收录",
                "explanation": "当前知识库暂时没有这条命令的详细解释。",
                "category": "其他",
                "knowledge": "后续版本可以继续扩充 H3C 命令知识库，或接入 AI 进行智能分析。",
                "scenario": "",
                "related_commands": [],
                "common_errors": [],
                "troubleshooting": "",
            }
            if spell:
                entry["spelling_error"] = spell
                spelling_errors.append(spell)
            else:
                entry["unmatched"] = True
                unmatched.append(line)
            parsed.append(entry)

    return {
        "parsed": parsed,
        "spelling_errors": spelling_errors,
        "unmatched": unmatched,
    }
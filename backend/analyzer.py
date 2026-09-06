"""
H3C 配置分析器 V3.0
整合：命令解析 + 拼写检查 + 配置检测 + 错误分析
"""
from parser import parse_config
from checker import check_vlan, check_interface, check_ip, check_completeness, calculate_score
from trunk_checker import check_trunk


def analyze_config(config: str):
    """
    完整分析 H3C 配置。
    返回: {
        "parsed": [...],
        "spelling_errors": [...],
        "unmatched": [...],
        "issues": [...],
        "score": {...},
        "error_commands": [...],  # 仅 errors + warnings，用于错误分析 Tab
    }
    """
    # 1. 解析（含拼写检查）
    parse_result = parse_config(config)
    parsed = parse_result["parsed"]
    spelling_errors = parse_result["spelling_errors"]
    unmatched = parse_result["unmatched"]

    # 2. 构建原始行列表
    parsed_lines = []
    for raw_line in config.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parsed_lines.append({"raw": line})

    # 3. 执行配置检测
    all_issues = []
    all_issues.extend(check_vlan(parsed_lines))
    all_issues.extend(check_interface(parsed_lines))
    all_issues.extend(check_trunk(parsed_lines))
    all_issues.extend(check_ip(parsed_lines))
    all_issues.extend(check_completeness(parsed_lines))

    # 4. 计算评分
    score = calculate_score(all_issues)

    # 5. 生成错误分析（仅 errors + warnings，不含 info）
    error_commands = _build_error_analysis(parsed_lines, all_issues, spelling_errors)

    return {
        "parsed": parsed,
        "spelling_errors": spelling_errors,
        "unmatched": unmatched,
        "issues": all_issues,
        "score": score,
        "error_commands": error_commands,
    }


def _build_error_analysis(parsed_lines, issues, spelling_errors):
    """
    构建错误分析列表：每条有问题的命令 + 错误详情 + 改进建议
    只包含 error 和 warning 级别的问题，info 级别不纳入错误分析
    """
    import re
    error_commands = []
    seen_keys = set()  # 避免重复

    # 从配置 issues 中提取错误
    for issue in issues:
        if issue["level"] not in ("error", "warning"):
            continue

        # 从问题消息中提取关键命令/资源
        msg = issue.get("message", "")
        detail = issue.get("detail", "")
        suggestion = issue.get("suggestion", "")

        # 尝试匹配接口名
        iface_match = re.search(r"接口\s+([\w\d/]+)", msg)
        # 尝试匹配 VLAN ID
        vlan_match = re.search(r"VLAN\s+(\d+)", msg)
        # 尝试匹配 IP
        ip_match = re.search(r"IP\s+地址\s+(\S+)", msg)

        # 确定 key（用于去重）
        key = None
        raw_display = None
        if iface_match:
            key = f"interface {iface_match.group(1)}"
            raw_display = f"interface {iface_match.group(1)}"
        elif vlan_match:
            key = f"vlan {vlan_match.group(1)}"
            raw_display = f"vlan {vlan_match.group(1)}"
        elif ip_match:
            key = f"ip {ip_match.group(1)}"
            raw_display = f"ip address {ip_match.group(1)}"

        if key is None:
            # 通用问题（如 save 缺失）
            key = f"__generic_{issue['module']}_{issue['level']}"
            raw_display = msg

        if key in seen_keys:
            # 追加到已有的 error_command
            for ec in error_commands:
                if ec.get("_key") == key:
                    ec["issues"].append({
                        "level": issue["level"],
                        "module": issue["module"],
                        "message": issue["message"],
                        "suggestion": suggestion,
                        "detail": detail,
                    })
                    if suggestion and suggestion not in ec["suggestions"]:
                        ec["suggestions"].append(suggestion)
                    break
            continue

        seen_keys.add(key)
        error_commands.append({
            "_key": key,
            "raw_command": raw_display,
            "issues": [{
                "level": issue["level"],
                "module": issue["module"],
                "message": issue["message"],
                "suggestion": suggestion,
                "detail": detail,
            }],
            "suggestions": [suggestion],
            "detail": detail,
        })

    # 添加拼写错误
    for spell_err in spelling_errors:
        key = f"__spell_{spell_err['original']}"
        if key not in seen_keys:
            seen_keys.add(key)
            error_commands.append({
                "_key": key,
                "raw_command": spell_err["original"],
                "issues": [{
                    "level": "warning",
                    "module": "拼写检查",
                    "message": f"命令拼写可能错误: {spell_err['original']}",
                    "suggestion": f"建议改为: {spell_err['suggestion']}",
                    "detail": spell_err.get("hint", f"编辑距离: {spell_err['distance']}"),
                }],
                "suggestions": [f"改为: {spell_err['suggestion']}"],
                "detail": spell_err.get("hint", ""),
            })

    # 移除内部 key
    for ec in error_commands:
        ec.pop("_key", None)

    return error_commands
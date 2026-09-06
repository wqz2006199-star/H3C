"""
H3C Trunk 检测模块 V3.1
检测：
1. Trunk 接口是否配置 permit vlan
2. 已创建 VLAN 是否被 Trunk 放行
3. Access / Trunk 配置冲突
4. 接口模式逻辑错误
5. Trunk 放行的 VLAN 是否已创建
"""

import re
from rules import TRUNK_RULES


def _extract_vlan_ids(tokens):
    """解析 permit vlan 后的 VLAN 列表，支持单个 ID、to 范围和 all。"""
    result = set()
    i = 0
    while i < len(tokens):
        token = tokens[i].lower()
        if token == "all":
            # H3C 的 all 表示允许所有 VLAN，无需逐一报缺失
            return None
        try:
            start = int(token)
        except ValueError:
            i += 1
            continue

        if i + 2 < len(tokens) and tokens[i + 1].lower() == "to":
            try:
                end = int(tokens[i + 2])
                if start <= end and end - start <= 4094:
                    result.update(range(start, end + 1))
                    i += 3
                    continue
            except ValueError:
                pass

        result.add(start)
        i += 1

    return result


def _collect_interfaces(lines):
    """按 interface/quit 追踪接口上下文，返回接口配置字典。"""
    interfaces = {}
    current = None

    for index, item in enumerate(lines):
        raw = item.get("raw", "").strip()
        if not raw or raw.startswith("#"):
            continue

        low = raw.lower()

        if low.startswith("interface "):
            parts = raw.split(None, 1)
            if len(parts) == 2:
                current = parts[1].strip()
                interfaces[current] = {
                    "index": index,
                    "link_type": None,
                    "access_vlans": [],
                    "trunk_vlans": set(),
                    "trunk_permit_seen": False,
                    "trunk_permit_all": False,
                    "trunk_permit_lines": [],
                    "access_vlan_lines": [],
                }
            continue

        if low in ("quit", "return"):
            current = None
            continue

        if current is None:
            continue

        cfg = interfaces[current]

        if low == "port link-type access":
            cfg["link_type"] = "access"
        elif low == "port link-type trunk":
            cfg["link_type"] = "trunk"
        elif low == "port link-type hybrid":
            cfg["link_type"] = "hybrid"

        if low.startswith("port access vlan "):
            parts = raw.split()
            if len(parts) >= 4:
                try:
                    cfg["access_vlans"].append(int(parts[-1]))
                except ValueError:
                    pass
            cfg["access_vlan_lines"].append(raw)

        if low.startswith("port trunk permit vlan "):
            parts = raw.split()
            try:
                vlan_pos = next(i for i, p in enumerate(parts) if p.lower() == "vlan")
                vlan_ids = _extract_vlan_ids(parts[vlan_pos + 1:])
                cfg["trunk_permit_seen"] = True
                cfg["trunk_permit_lines"].append(raw)
                if vlan_ids is None:
                    cfg["trunk_permit_all"] = True
                else:
                    cfg["trunk_vlans"].update(vlan_ids)
            except StopIteration:
                pass

    return interfaces


def _collect_created_vlans(lines):
    """提取 vlan / vlan batch 创建的 VLAN。"""
    vlans = set()

    for item in lines:
        raw = item.get("raw", "").strip()
        low = raw.lower()

        if low.startswith("vlan batch "):
            parts = raw.split()[2:]
            ids = _extract_vlan_ids(parts)
            if ids is not None:
                vlans.update(v for v in ids if 1 <= v <= 4094)

        elif re.fullmatch(r"vlan\s+\d+", low):
            try:
                vid = int(raw.split()[1])
                if 1 <= vid <= 4094:
                    vlans.add(vid)
            except (ValueError, IndexError):
                pass

    return vlans


def check_trunk(lines):
    """
    Trunk 专项检测。

    返回统一 issues 结构，便于直接接入 checker/analyzer/frontend。
    """
    issues = []
    created_vlans = _collect_created_vlans(lines)
    interfaces = _collect_interfaces(lines)

    for iface, cfg in interfaces.items():
        mode = cfg["link_type"]

        # 规则 1：Trunk 必须允许 VLAN
        if mode == "trunk" and not cfg["trunk_permit_seen"]:
            issues.append({
                "level": "error",
                "module": "Trunk",
                "rule_id": "TRUNK-001",
                "message": f"接口 {iface} 配置为 Trunk 模式但未放行任何 VLAN",
                "suggestion": "增加: port trunk permit vlan <VLAN_ID>",
                "detail": f"接口 {iface} 已配置 port link-type trunk，但没有检测到 port trunk permit vlan。"
            })

        # 规则 2：已创建 VLAN 是否通过 Trunk
        # all 表示全部放行；没有创建 VLAN 时不生成缺失项。
        if mode == "trunk" and cfg["trunk_permit_seen"] and not cfg["trunk_permit_all"]:
            for vid in sorted(created_vlans - cfg["trunk_vlans"]):
                issues.append({
                    "level": "warning",
                    "module": "Trunk",
                    "rule_id": "TRUNK-002",
                    "message": f"VLAN {vid}没有通过Trunk接口 {iface}",
                    "suggestion": f"在接口 {iface} 下执行: port trunk permit vlan {vid}",
                    "detail": f"设备已创建 VLAN {vid}，但接口 {iface} 的 Trunk 放行列表中未包含该 VLAN。"
                })

        # 规则 3：Access / Trunk 配置冲突
        if mode == "access" and cfg["trunk_permit_seen"]:
            issues.append({
                "level": "error",
                "module": "Trunk",
                "rule_id": "TRUNK-003",
                "message": f"接口 {iface} 存在 Access / Trunk 配置冲突",
                "suggestion": "删除 port trunk permit vlan，或者将接口修改为 Trunk 模式",
                "detail": f"接口 {iface} 当前为 Access 模式，却配置了: {'; '.join(cfg['trunk_permit_lines'])}"
            })

        if mode == "trunk" and cfg["access_vlans"]:
            access_vlans = ", ".join(str(v) for v in sorted(set(cfg["access_vlans"])))
            issues.append({
                "level": "error",
                "module": "Trunk",
                "rule_id": "TRUNK-003",
                "message": f"接口 {iface} 存在 Trunk / Access VLAN 配置冲突",
                "suggestion": "删除 port access vlan <VLAN_ID>，或将接口修改为 Access 模式",
                "detail": f"接口 {iface} 当前为 Trunk 模式，却配置了 Access VLAN: {access_vlans}。"
            })

        # 规则 4：接口模式逻辑错误
        if mode is None and cfg["trunk_permit_seen"]:
            issues.append({
                "level": "warning",
                "module": "Trunk",
                "rule_id": "TRUNK-004",
                "message": f"接口 {iface} 未明确配置接口模式，但存在 Trunk 命令",
                "suggestion": "增加: port link-type trunk，或删除 port trunk permit vlan",
                "detail": f"接口 {iface} 没有检测到 port link-type access/trunk/hybrid。"
            })

        if mode is None and cfg["access_vlans"]:
            issues.append({
                "level": "warning",
                "module": "Interface",
                "rule_id": "TRUNK-004",
                "message": f"接口 {iface} 未明确配置接口模式，但存在 Access VLAN 命令",
                "suggestion": "增加: port link-type access，或检查接口配置",
                "detail": f"接口 {iface} 没有检测到明确的接口模式。"
            })

        # Trunk 放行未创建 VLAN
        if mode == "trunk" and not cfg["trunk_permit_all"]:
            for vid in sorted(cfg["trunk_vlans"]):
                if vid not in created_vlans:
                    issues.append({
                        "level": "error",
                        "module": "Trunk",
                        "rule_id": "TRUNK-005",
                        "message": f"接口 {iface} 的 Trunk 放行了未创建的 VLAN {vid}",
                        "suggestion": f"创建 VLAN: vlan {vid}，或删除该 VLAN 的 Trunk 放行配置",
                        "detail": f"接口 {iface} 允许 VLAN {vid} 通过，但配置中未找到 vlan {vid}。"
                    })

    return issues

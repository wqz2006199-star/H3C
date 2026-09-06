"""
H3C 配置检测模块 V3.0
包含 VLAN、接口、IP、完整性检测规则
所有检测逻辑去重，每个问题只报告一次
"""


def _get_created_vlans(parsed_lines):
    """从配置行中提取所有已创建的 VLAN ID"""
    vlans = set()
    for line in parsed_lines:
        raw = line.get("raw", "").strip()
        if raw.startswith("vlan ") and not raw.startswith("vlan batch"):
            parts = raw.split()
            if len(parts) >= 2:
                try:
                    vlans.add(int(parts[1]))
                except ValueError:
                    pass
        elif raw.startswith("vlan batch"):
            parts = raw.split()
            for p in parts[1:]:
                if "-" in p:
                    try:
                        s, e = p.split("-")
                        for v in range(int(s), int(e) + 1):
                            vlans.add(v)
                    except ValueError:
                        pass
                else:
                    try:
                        vlans.add(int(p))
                    except ValueError:
                        pass
    return vlans


def _get_current_interface(parsed_lines, target_index):
    """从目标行向上查找最近的 interface 命令，返回接口名"""
    for i in range(target_index, -1, -1):
        raw = parsed_lines[i].get("raw", "").strip()
        if raw.startswith("interface ") or raw.startswith("vlanif ") or raw.startswith("Vlanif "):
            parts = raw.split()
            if len(parts) >= 2:
                return parts[1]
    return "系统视图"


def _is_valid_ip(ip):
    """检查 IP 地址格式是否合法"""
    try:
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        for p in parts:
            num = int(p)
            if num < 0 or num > 255:
                return False
        return True
    except (ValueError, AttributeError):
        return False


def _is_valid_mask(mask):
    """检查子网掩码是否合法"""
    valid_masks = {
        "255.255.255.0", "255.255.255.128", "255.255.255.192",
        "255.255.255.224", "255.255.255.240", "255.255.255.248",
        "255.255.255.252", "255.255.255.254",
        "255.255.254.0", "255.255.252.0", "255.255.248.0",
        "255.255.240.0", "255.255.224.0", "255.255.192.0",
        "255.255.128.0", "255.255.0.0", "255.254.0.0",
        "255.252.0.0", "255.248.0.0", "255.240.0.0",
        "255.224.0.0", "255.192.0.0", "255.128.0.0",
        "255.0.0.0", "0.0.0.0"
    }
    return mask in valid_masks


def check_vlan(parsed_lines):
    """
    VLAN 配置检测
    只检测：VLAN 被使用但未创建、已创建但未绑定端口、VLAN ID 范围
    不检测接口相关的 VLAN 问题（由 check_interface 负责）
    """
    issues = []
    created_vlans = _get_created_vlans(parsed_lines)
    used_vlans = set()
    vlan_port_map = {}  # vlan_id -> [interface names]

    for i, line in enumerate(parsed_lines):
        raw = line.get("raw", "").strip()

        # 提取 port access vlan XXX
        if raw.startswith("port access vlan"):
            parts = raw.split()
            if len(parts) >= 3:
                try:
                    vid = int(parts[-1])
                    used_vlans.add(vid)
                    iface = _get_current_interface(parsed_lines, i)
                    if vid not in vlan_port_map:
                        vlan_port_map[vid] = []
                    vlan_port_map[vid].append(iface)
                except ValueError:
                    pass

        # 提取 port trunk permit vlan XXX
        if raw.startswith("port trunk permit vlan"):
            parts = raw.split()
            try:
                vlan_idx = parts.index("vlan")
                for p in parts[vlan_idx + 1:]:
                    vid = int(p)
                    used_vlans.add(vid)
                    iface = _get_current_interface(parsed_lines, i)
                    if vid not in vlan_port_map:
                        vlan_port_map[vid] = []
                    vlan_port_map[vid].append(iface)
            except (ValueError, IndexError):
                pass

    # 只报告：已使用但未创建的 VLAN
    for vid in sorted(used_vlans - created_vlans):
        ports = vlan_port_map.get(vid, [])
        port_list = ", ".join(sorted(set(ports))) if ports else "未指定"
        issues.append({
            "level": "error",
            "module": "VLAN",
            "message": f"VLAN {vid} 被使用但未创建",
            "suggestion": f"在系统视图下执行: vlan {vid}",
            "detail": f"配置中引用了 VLAN {vid}（端口: {port_list}），但未找到对应的 vlan {vid} 命令。"
        })

    # 只报告：已创建但未绑定任何端口的 VLAN
    for vid in sorted(created_vlans - used_vlans):
        issues.append({
            "level": "warning",
            "module": "VLAN",
            "message": f"VLAN {vid} 已创建但未绑定任何端口",
            "suggestion": f"如需使用请配置接口: interface + port access vlan {vid}",
            "detail": f"VLAN {vid} 已创建但没有任何接口加入该 VLAN。"
        })

    # VLAN ID 范围检查
    for vid in sorted(created_vlans | used_vlans):
        if vid < 1 or vid > 4094:
            issues.append({
                "level": "error",
                "module": "VLAN",
                "message": f"VLAN ID {vid} 超出有效范围 (1-4094)",
                "suggestion": "请修改为 1-4094 范围内的有效 VLAN ID",
                "detail": ""
            })

    return issues


def check_interface(parsed_lines):
    """
    接口配置检测
    检测：Access 接口缺少 VLAN、Trunk 接口缺少 permit、Trunk 允许未创建 VLAN、VLANIF 缺少 IP
    """
    issues = []
    current_iface = None
    iface_cfg = {}

    for i, line in enumerate(parsed_lines):
        raw = line.get("raw", "").strip()
        if not raw:
            continue

        # 追踪当前接口
        if raw.startswith("interface ") or raw.startswith("vlanif ") or raw.startswith("Vlanif "):
            parts = raw.split()
            if len(parts) >= 2:
                current_iface = parts[1]
                iface_cfg[current_iface] = {
                    "link_type": None, "access_vlan": None,
                    "trunk_vlans": [], "ip": None
                }

        elif current_iface and current_iface in iface_cfg:
            cfg = iface_cfg[current_iface]

            if raw.startswith("port link-type access"):
                cfg["link_type"] = "access"
            elif raw.startswith("port link-type trunk"):
                cfg["link_type"] = "trunk"
            elif raw.startswith("port link-type hybrid"):
                cfg["link_type"] = "hybrid"

            if raw.startswith("port access vlan"):
                parts = raw.split()
                if len(parts) >= 3:
                    try:
                        cfg["access_vlan"] = int(parts[-1])
                    except ValueError:
                        pass

            if raw.startswith("port trunk permit vlan"):
                parts = raw.split()
                try:
                    vlan_idx = parts.index("vlan")
                    for p in parts[vlan_idx + 1:]:
                        try:
                            cfg["trunk_vlans"].append(int(p))
                        except ValueError:
                            pass
                except ValueError:
                    pass

            if raw.startswith("ip address"):
                parts = raw.split()
                if len(parts) >= 4:
                    cfg["ip"] = f"{parts[2]} {parts[3]}"

    created_vlans = _get_created_vlans(parsed_lines)

    for iface, cfg in iface_cfg.items():
        # Access 接口缺少 VLAN 绑定
        if cfg["link_type"] == "access" and cfg["access_vlan"] is None and not cfg["trunk_vlans"]:
            issues.append({
                "level": "error",
                "module": "Interface",
                "message": f"接口 {iface} 配置为 Access 模式但未绑定 VLAN",
                "suggestion": f"增加: port access vlan <VLAN_ID>",
                "detail": f"接口 {iface} 已设置为 Access 模式，但未使用 port access vlan 命令绑定 VLAN。"
            })

        # VLANIF 接口缺少 IP
        if cfg["link_type"] is None and cfg["ip"] is None:
            if "vlanif" in iface.lower() or "Vlanif" in iface:
                issues.append({
                    "level": "warning",
                    "module": "Interface",
                    "message": f"VLAN 接口 {iface} 未配置 IP 地址",
                    "suggestion": f"增加: ip address <IP> <MASK>",
                    "detail": f"VLAN 接口 {iface} 通常需要配置 IP 地址作为该 VLAN 的网关。"
                })

    return issues


def check_ip(parsed_lines):
    """IP 地址检测：格式校验、重复 IP、默认路由"""
    issues = []
    ip_list = []  # [(interface, ip, mask), ...]

    for i, line in enumerate(parsed_lines):
        raw = line.get("raw", "").strip()
        if not raw.startswith("ip address"):
            continue

        parts = raw.split()
        if len(parts) < 4:
            continue

        ip = parts[2]
        mask = parts[3]
        iface = _get_current_interface(parsed_lines, i)

        # IP 格式检查
        if not _is_valid_ip(ip):
            issues.append({
                "level": "error",
                "module": "IP",
                "message": f"接口 {iface} 的 IP 地址格式错误: {ip}",
                "suggestion": "请检查 IP 地址格式，正确示例: 192.168.1.1",
                "detail": ""
            })

        # 子网掩码格式检查
        if not _is_valid_mask(mask):
            issues.append({
                "level": "error",
                "module": "IP",
                "message": f"接口 {iface} 的子网掩码格式错误: {mask}",
                "suggestion": "请检查子网掩码格式，正确示例: 255.255.255.0",
                "detail": ""
            })

        # 重复 IP 检测
        for ex_iface, ex_ip, ex_mask in ip_list:
            if ip == ex_ip:
                issues.append({
                    "level": "error",
                    "module": "IP",
                    "message": f"IP 地址 {ip} 在接口 {iface} 和 {ex_iface} 重复配置",
                    "suggestion": f"请检查接口 {ex_iface} 和 {iface} 的 IP 配置，避免地址冲突",
                    "detail": f"发现重复的 IP 地址 {ip}，分别配置在接口 {ex_iface} 和 {iface}。"
                })

        if _is_valid_ip(ip) and _is_valid_mask(mask):
            ip_list.append((iface, ip, mask))

    # 默认路由检查
    has_default_route = any(
        line.get("raw", "").strip().startswith("ip route-static 0.0.0.0 0.0.0.0")
        for line in parsed_lines
    )
    has_ip_config = any(raw.startswith("ip address") for raw in [l.get("raw", "").strip() for l in parsed_lines])

    if has_ip_config and not has_default_route:
        issues.append({
            "level": "info",
            "module": "IP",
            "message": "未检测到默认路由（ip route-static 0.0.0.0 0.0.0.0）",
            "suggestion": "如需访问外网，建议配置默认路由: ip route-static 0.0.0.0 0.0.0.0 <网关IP>",
            "detail": "当前配置中没有默认路由，设备可能无法访问外部网络。"
        })

    return issues


def check_completeness(parsed_lines):
    """配置完整性检测：save、system-view"""
    issues = []

    has_save = any(line.get("raw", "").strip() == "save" for line in parsed_lines)
    if not has_save:
        issues.append({
            "level": "warning",
            "module": "完整性",
            "message": "配置中未检测到 save 命令",
            "suggestion": "在系统视图下执行 save 保存配置，避免重启后丢失",
            "detail": "完成配置后应及时保存，建议配置末尾增加 save 命令。"
        })

    has_system_view = any(line.get("raw", "").strip() == "system-view" for line in parsed_lines)
    if not has_system_view:
        issues.append({
            "level": "info",
            "module": "完整性",
            "message": "配置中未检测到 system-view 命令",
            "suggestion": "建议配置开头增加 system-view 进入系统视图",
            "detail": "如果配置是从用户视图开始粘贴的，建议先执行 system-view 进入系统视图。"
        })

    return issues


def calculate_score(all_issues):
    """根据问题计算评分 (0-100)"""
    score = 100
    error_count = 0
    warning_count = 0
    info_count = 0

    for issue in all_issues:
        level = issue.get("level", "info")
        if level == "error":
            score -= 15
            error_count += 1
        elif level == "warning":
            score -= 8
            warning_count += 1
        else:
            score -= 3
            info_count += 1

    score = max(0, score)

    if error_count == 0 and warning_count == 0:
        risk_level = "低"
    elif error_count <= 2:
        risk_level = "中"
    else:
        risk_level = "高"

    return {
        "score": score,
        "risk_level": risk_level,
        "error_count": error_count,
        "warning_count": warning_count,
        "info_count": info_count
    }
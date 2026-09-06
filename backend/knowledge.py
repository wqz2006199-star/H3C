"""H3C 知识学习与分类体系模块 V3.2.2 + V1.4.1
统一使用 knowledge_base/network_commands.json 作为知识数据源。
分类树负责展示层级，模块映射负责把 80 条 JSON 命令挂到对应学习分类。
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KB_PATH = BASE_DIR / "knowledge_base" / "network_commands.json"

CATEGORY_TREE = {
    "基础操作": {"desc": "设备视图切换、基础命令", "children": []},
    "系统管理": {"desc": "设备系统、版本、启动与维护", "children": ["配置维护", "查看与维护"]},
    "二层交换": {"desc": "VLAN、接口、二层控制等交换配置", "children": ["VLAN", "接口配置", "二层控制"]},
    "三层网络": {"desc": "IP、路由等三层能力", "children": ["三层配置", "动态路由"]},
    "安全与服务": {"desc": "ACL、DHCP、NAT、AAA、远程管理等", "children": ["安全配置", "DHCP", "NAT", "远程管理"]},
}

# JSON 知识库 module -> 页面学习分类
MODULE_TO_CATEGORY = {
    "VLAN": "VLAN",
    "Interface": "接口配置",
    "IP": "三层配置",
    "Static Route": "三层配置",
    "OSPF": "动态路由",
    "ACL": "安全配置",
    "DHCP": "DHCP",
    "NAT": "NAT",
    "AAA": "安全配置",
    "SSH": "远程管理",
    "STP": "二层控制",
    "Link Aggregation": "二层控制",
    "QoS": "二层控制",
    "System": "配置维护",
    "Display": "查看与维护",
    "SNMP": "查看与维护",
    "NTP": "查看与维护",
}

# 学习卡片的基础说明；命令本身统一从 JSON 动态读取
LEARNING = {
    "VLAN": {
        "title": "VLAN 基础", "level": "入门",
        "summary": "VLAN 将交换网络划分为多个逻辑广播域。",
        "steps": ["创建 VLAN", "把 Access 端口加入 VLAN", "交换机互联时使用 Trunk", "确认 Trunk 放行所需 VLAN"],
    },
    "接口配置": {
        "title": "接口配置", "level": "入门",
        "summary": "接口配置的核心是先确定接口角色，再配置对应参数。",
        "steps": ["确认接口编号", "选择 Access/Trunk/三层模式", "配置 VLAN 或 IP", "使用 display 命令验证"],
    },
    "二层控制": {
        "title": "二层控制", "level": "进阶",
        "summary": "通过 STP、链路聚合和 QoS 等能力提升二层网络可靠性与业务质量。",
        "steps": ["确认二层拓扑", "配置生成树或链路聚合", "按业务需要配置 QoS", "使用 display 命令验证状态"],
    },
    "三层配置": {
        "title": "三层接口与 IP", "level": "进阶",
        "summary": "三层接口负责 IP 通信，常见能力包括接口地址和静态路由。",
        "steps": ["确认接口已经是三层接口", "配置 IP 与掩码", "配置静态路由或默认路由", "检查网关和路由表"],
    },
    "动态路由": {
        "title": "动态路由", "level": "进阶",
        "summary": "通过 OSPF 等协议自动学习网络路由，适合多网段网络。",
        "steps": ["规划 Router ID", "启用 OSPF", "创建区域", "宣告接口网段", "验证邻居与路由表"],
    },
    "安全配置": {
        "title": "安全配置", "level": "进阶",
        "summary": "通过 ACL、AAA 等机制限制不必要的网络访问并加强设备管理安全。",
        "steps": ["明确保护对象", "设计允许/拒绝规则", "应用到正确接口或服务", "验证命中情况"],
    },
    "DHCP": {
        "title": "DHCP", "level": "进阶",
        "summary": "自动为终端分配 IP、网关、DNS 等网络参数。",
        "steps": ["启用 DHCP", "创建地址池", "配置网段与网关", "检查地址租约"],
    },
    "NAT": {
        "title": "NAT", "level": "进阶",
        "summary": "实现私网地址与公网地址之间的转换。",
        "steps": ["明确内外网接口", "规划转换规则", "应用 NAT", "检查会话和连通性"],
    },
    "远程管理": {
        "title": "远程管理", "level": "进阶",
        "summary": "通过 SSH 等方式安全地远程管理网络设备。",
        "steps": ["配置管理地址", "创建认证账号", "启用安全远程管理服务", "验证远程登录"],
    },
    "配置维护": {
        "title": "配置维护", "level": "入门",
        "summary": "围绕设备配置保存、查看和维护进行日常管理。",
        "steps": ["查看当前配置", "确认修改内容", "保存配置", "必要时备份配置"],
    },
    "查看与维护": {
        "title": "查看与维护", "level": "入门",
        "summary": "先看状态、再看配置、最后定位故障，是网络排障的基本流程。",
        "steps": ["查看接口状态", "查看 VLAN 与路由", "查看当前配置", "根据异常继续深入检查"],
    },
    "基础操作": {
        "title": "基础操作", "level": "入门",
        "summary": "掌握设备视图切换和常用基础操作命令。",
        "steps": ["进入系统视图", "进入目标配置视图", "执行配置", "使用 quit/return 返回"],
    },
}


def load_network_knowledge():
    """加载统一 JSON 知识库；文件异常时返回空列表。"""
    try:
        with KB_PATH.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _commands_by_category():
    grouped = {name: [] for name in LEARNING}
    for item in load_network_knowledge():
        module = item.get("module", "")
        category = MODULE_TO_CATEGORY.get(module)
        if category in grouped:
            grouped[category].append(item)
    return grouped


def _root_for_category(category):
    if category in CATEGORY_TREE:
        return category
    for root, data in CATEGORY_TREE.items():
        if category in data["children"]:
            return root
    return None


def get_categories():
    """返回分类树，并用 JSON 80 条知识命令计算准确数量。"""
    grouped = _commands_by_category()
    result = []
    for root, data in CATEGORY_TREE.items():
        cats = [root] + data["children"]
        count = sum(len(grouped.get(c, [])) for c in cats)
        result.append({
            "name": root,
            "description": data["desc"],
            "children": data["children"],
            "count": count,
            "child_counts": {c: len(grouped.get(c, [])) for c in data["children"]},
        })
    return result


def get_knowledge(category=None):
    """按根分类或子分类返回学习卡片。

    关键修复：
    选择“三级网络”等根分类时，会同时返回其所有子分类，
    不再因为根分类本身没有 LEARNING 卡片而显示“暂无内容”。
    """
    grouped = _commands_by_category()

    if category:
        root = _root_for_category(category)
        if root is None:
            selected = [category]
        elif category in CATEGORY_TREE:
            selected = CATEGORY_TREE[category]["children"]
            # 根分类没有独立命令时，直接展示其全部子分类
            if not selected:
                selected = [category]
        else:
            selected = [category]
    else:
        selected = list(LEARNING.keys())

    items = []
    for cat in selected:
        lesson = LEARNING.get(cat)
        if not lesson:
            continue

        kb_items = grouped.get(cat, [])
        # 优先使用 JSON syntax，确保知识学习中的命令与知识库完全一致
        json_commands = [
            item.get("syntax") or item.get("command", "")
            for item in kb_items
            if item.get("syntax") or item.get("command")
        ]

        item = dict(lesson)
        item["category"] = cat
        item["command_count"] = len(kb_items)
        item["commands"] = list(dict.fromkeys(json_commands))
        # 给前端详情使用
        item["command_items"] = [
            {
                "command": x.get("command", ""),
                "syntax": x.get("syntax", ""),
                "module": x.get("module", ""),
                "description": x.get("description", ""),
                "example": x.get("example", ""),
                "errors": x.get("errors", []),
                "troubleshooting": x.get("troubleshooting", []),
                "related_commands": x.get("related_commands", []),
            }
            for x in kb_items
        ]
        items.append(item)

    return items

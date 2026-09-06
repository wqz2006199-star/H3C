"""
H3C 配置检测规则定义 V3.1
用于统一维护检测规则编号、等级和说明。
"""

TRUNK_RULES = {
    "TRUNK-001": {
        "title": "Trunk 未放行 VLAN",
        "level": "error",
        "description": "Trunk 接口必须配置 port trunk permit vlan。",
    },
    "TRUNK-002": {
        "title": "Trunk VLAN 未放行",
        "level": "warning",
        "description": "已创建并需要使用的 VLAN 应包含在 Trunk 放行列表中。",
    },
    "TRUNK-003": {
        "title": "Access / Trunk 配置冲突",
        "level": "error",
        "description": "Access 接口不应配置 Trunk 专用命令，Trunk 接口不应配置 Access VLAN。",
    },
    "TRUNK-004": {
        "title": "接口模式逻辑错误",
        "level": "warning",
        "description": "出现 Access/Trunk 专用命令时，应明确配置对应接口模式。",
    },
    "TRUNK-005": {
        "title": "Trunk 放行未创建 VLAN",
        "level": "error",
        "description": "Trunk permit VLAN 列表中的 VLAN 应已在设备上创建。",
    },
}

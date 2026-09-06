# H3C 配置智能解析平台 V3.0

> 从"命令解释工具"升级为"配置智能分析平台"——不仅能解释每条命令，还能自动检测配置问题并给出修改建议。

---

## 功能特性

| 功能 | 说明 |
|------|------|
| **命令解析** | 逐行识别 H3C 配置命令，显示中文解释、扩展知识、适用场景 |
| **配置检测** | 自动分析配置中的错误和隐患，覆盖 VLAN、接口、Trunk、IP 四大模块 |
| **风险评分** | 对配置进行 0-100 分评分，直观反映配置质量 |
| **修改建议** | 每个问题都附带具体的修复命令，直接可用 |
| **100+ 命令库** | 覆盖 VLAN、OSPF、NAT、DHCP、安全等常用场景 |

---

## 配置检测规则（V3.1 新增 Trunk 专项检测）

### VLAN 检测
- 检查使用的 VLAN 是否已创建
- 检查 VLAN ID 是否在有效范围（1-4094）
- 检查已创建的 VLAN 是否有端口绑定

### 接口检测
- Access 接口是否绑定了 VLAN
- Trunk 接口是否允许了 VLAN
- Trunk 允许的 VLAN 是否已创建
- VLANIF 接口是否配置了 IP 地址

### Trunk 检测
- Trunk 端口是否配置了 permit vlan
- 已创建 VLAN 是否被 Trunk 放行
- Trunk 放行的 VLAN 是否已创建
- Access / Trunk 配置冲突
- 接口模式逻辑错误（未明确模式却出现 Access/Trunk 专用命令）
- 支持 `port trunk permit vlan 10 20`、`10 to 20`、`all` 等常见写法

### IP 检测
- IP 地址格式校验
- 子网掩码格式校验
- 重复 IP 地址检测
- 默认路由缺失提示

### 完整性检测
- 是否执行了 save 保存配置
- 是否进入 system-view 系统视图

---

## 快速开始

### 第一次运行

1. 确认已安装 Python 3.10+，命令行输入 `python --version` 检查
2. 双击 `install.bat` 安装依赖
3. 双击 `start.bat` 启动服务
4. 浏览器自动打开：`http://127.0.0.1:5500`

### 运行说明

启动后保持两个命令行窗口不关闭：
- **Backend**（端口 8000）：FastAPI 后端
- **Frontend**（端口 5500）：网页服务

---

## 页面说明

### 命令解析 Tab
显示每条命令的：标题、解释、扩展知识、适用场景、相关命令、常见错误、排错方法。

### 配置检测 Tab
显示：
- **风险评分卡片**：分数 + 风险等级 + 问题统计
- **问题列表**：按严重程度排列，每个问题可展开查看详细信息和修复建议

---

## 项目结构

```
v3/
├── backend/
│   ├── main.py          # FastAPI 入口，提供 /api/parse 和 /api/analyze 两个接口
│   ├── parser.py        # 命令解析器
│   ├── command_db.py    # H3C 命令知识库（100+ 条）
│   ├── checker.py       # 配置检测核心（VLAN/接口/Trunk/IP/完整性检测）
│   ├── trunk_checker.py  # Trunk 专项检测
│   ├── rules.py          # 检测规则定义
│   ├── analyzer.py      # 分析器，整合解析和检测
│   └── requirements.txt
├── frontend/
│   └── index.html       # 前端页面（Tab 切换 + 评分 + 问题列表）
├── examples/
│   └── h3c_config.txt   # 示例配置
├── install.bat          # 一键安装依赖
├── start.bat            # 一键启动服务
└── README.md
```

---

## API 接口

### POST /api/parse
返回命令解析结果（兼容 V2.0）。

### POST /api/analyze
返回完整分析结果，包含命令解析、检测问题和风险评分。

**请求示例：**
```json
{
  "config": "system-view\nvlan 10\ninterface Gi1/0/1\nport link-type access\nport access vlan 10"
}
```

**响应示例：**
```json
{
  "parsed": [...],
  "issues": [
    {
      "level": "error",
      "module": "VLAN",
      "message": "VLAN 20 被使用但未创建",
      "suggestion": "在系统视图下执行: vlan 20",
      "detail": "..."
    }
  ],
  "score": {
    "score": 72,
    "risk_level": "中",
    "error_count": 1,
    "warning_count": 1,
    "info_count": 1
  }
}
```

---

## 常见问题

**Q：点击"开始解析"没反应？**
确保后端在前台运行（双击 start.bat），且浏览器访问的是 `http://127.0.0.1:5500` 而非直接打开 html 文件。

**Q：如何添加更多检测规则？**
编辑 `backend/checker.py`，在对应检测类中添加新的检查逻辑。

**Q：如何添加更多 H3C 命令？**
编辑 `backend/command_db.py`，按现有格式添加新条目即可。

---

## 版本历史

### V3.1（当前）
- 新增：Trunk 专项检测模块 `trunk_checker.py`
- 新增：Trunk VLAN 未放行检测
- 新增：Access / Trunk 配置冲突检测
- 新增：接口模式逻辑错误检测
- 新增：Trunk 未创建 VLAN 检测

### V3.0
- 新增：配置检测模块（VLAN/接口/Trunk/IP/完整性）
- 新增：风险评分系统（0-100 分，四档风险等级）
- 新增：修改建议，每个问题附带具体修复命令
- 新增：Tab 切换界面（命令解析 / 配置检测）
- 升级：后端新增 `/api/analyze` 接口

### V2.0
- 扩充命令库至 100+ 条
- 新增适用场景、相关命令、常见错误、排错方法
- 新增命令详情展开/收起交互
- 优化界面样式

### V1.0
- 基础命令解析功能
- 14 条常用命令知识库


## V1.4.1 智能命令分析
本阶段直接建立在 V3.2.2 全部知识数据包整合版之上，统一使用 `knowledge_base/network_commands.json`（80 条命令）。新增逐行命令识别、模块分类、基础上下文、拼写纠错、修改建议、搜索、自动补全和知识详情。

新增 API：`POST /api/intelligent/analyze`、`GET /api/autocomplete`、`GET /api/intelligent/search`、`GET /api/command/detail`。


## V1.4.1 分类修复
- 知识学习分类与 `knowledge_base/network_commands.json` 统一。
- 根分类点击后会加载对应全部子分类内容。
- 80 条 JSON 命令均有明确学习分类映射。
- 分类统计与 JSON 知识库数量一致，共 80 条。
- 分类标签和下拉框支持直接选择子分类。

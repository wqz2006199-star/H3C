from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from analyzer import analyze_config
from command_db import COMMAND_DB
from knowledge import get_categories, get_knowledge
from v14_analyzer import analyze_config as analyze_v14, search_commands as search_v14, autocomplete as autocomplete_v14, command_detail
import re

app = FastAPI(title="H3C 配置智能解析平台", version="3.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConfigRequest(BaseModel):
    config: str


class SearchRequest(BaseModel):
    keyword: str


class IntelligentRequest(BaseModel):
    config: str


@app.get("/")
def root():
    return {"message": "H3C 配置智能解析平台 V3.2 已启动"}


@app.post("/api/parse")
def parse(request: ConfigRequest):
    """兼容 V2.0：仅返回命令解析结果"""
    from parser import parse_config
    result = parse_config(request.config)
    return {"results": result["parsed"]}


@app.post("/api/intelligent/analyze")
def intelligent_analyze(request: IntelligentRequest):
    results = analyze_v14(request.config)
    return {"success": True, "version": "1.4.1", "results": results, "total": len(results), "recognized": sum(1 for x in results if x.get("recognized")), "spelling_errors": [x for x in results if x.get("type") == "命令拼写错误"]}


@app.get("/api/autocomplete")
def autocomplete(q: str = "", limit: int = 10):
    return {"results": autocomplete_v14(q, limit)}


@app.get("/api/command/detail")
def command_knowledge(command: str = ""):
    item = command_detail(command)
    return {"found": item is not None, "result": item}


@app.get("/api/intelligent/search")
def intelligent_search(q: str = "", limit: int = 20):
    rows = search_v14(q, limit)
    return {"results": rows, "total": len(rows)}


@app.post("/api/analyze")
def analyze(request: ConfigRequest):
    """完整分析：解析 + 拼写检查 + 配置检测 + 错误分析"""
    return analyze_config(request.config)


@app.get("/api/knowledge/categories")
def knowledge_categories():
    return {"categories": get_categories()}


@app.get("/api/knowledge")
def knowledge(category: str = ""):
    return {"lessons": get_knowledge(category or None)}


@app.post("/api/search")
def search(request: SearchRequest):
    """
    搜索命令知识库
    支持：关键词匹配命令关键字、标题、分类
    返回：匹配的命令列表（按相关性排序）
    """
    keyword = request.keyword.strip().lower()
    if not keyword:
        return {"results": [], "total": 0}
    kb_results = search_v14(keyword, 50)
    if kb_results:
        results = []
        for info in kb_results:
            results.append({"command":info.get("command",""),"title":info.get("description",""),"category":info.get("module","其他"),"explanation":info.get("description",""),"knowledge":info.get("scenes",""),"scenario":info.get("scenes",""),"related_commands":info.get("related_commands",[]),"common_errors":info.get("errors",[]),"troubleshooting":"；".join(info.get("troubleshooting",[])) if isinstance(info.get("troubleshooting",[]),list) else info.get("troubleshooting",""),"score":100,"match_type":"json_knowledge"})
        return {"results":results,"total":len(results)}

    results = []
    for cmd_key, info in COMMAND_DB.items():
        score = 0
        match_type = "other"

        # 精确匹配命令关键字
        if cmd_key.startswith(keyword):
            score += 100 - len(cmd_key)  # 越短优先级越高
            match_type = "command"
        # 匹配标题
        title = info.get("title", "").lower()
        if keyword in title:
            score += 50
            match_type = "title"
        # 匹配分类
        category = info.get("category", "").lower()
        if keyword in category:
            score += 30
            match_type = "category"
        # 匹配解释
        explanation = info.get("explanation", "").lower()
        if keyword in explanation:
            score += 20
            match_type = "explanation"

        if score > 0:
            results.append({
                "command": cmd_key,
                "title": info.get("title", ""),
                "category": info.get("category", ""),
                "explanation": info.get("explanation", ""),
                "knowledge": info.get("knowledge", ""),
                "scenario": info.get("scenario", ""),
                "related_commands": info.get("related_commands", []),
                "score": score,
                "match_type": match_type,
            })

    # 按 score 降序排列
    results.sort(key=lambda x: x["score"], reverse=True)
    return {"results": results, "total": len(results)}
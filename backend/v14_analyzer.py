"""V1.4 智能命令分析引擎"""
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from command_db import COMMAND_DB
KB_PATH = Path(__file__).resolve().parent.parent / "knowledge_base" / "network_commands.json"
def load_kb():
    with KB_PATH.open("r", encoding="utf-8-sig") as f:
        data=json.load(f)
    return data if isinstance(data,list) else []
def norm(s): return re.sub(r"\s+"," ",(s or "").strip().lower())
def command_match(line,item):
    n=norm(line); cmd=norm(item.get("command","")); syntax=norm(item.get("syntax",""))
    return bool(cmd and (n==cmd or n.startswith(cmd+" ") or (syntax and n==syntax)))
def fuzzy_match(line,kb):
    parts=norm(line).split()
    if not parts: return None,0.0
    best_item,best_score=None,0.0
    for item in kb:
        cmd=norm(item.get("command","")); syntax=norm(item.get("syntax",""))
        if not cmd: continue
        cand=cmd.split(); first=SequenceMatcher(None,parts[0],cand[0]).ratio(); score=first
        if len(parts)>1 and len(cand)>1:
            tail=min(len(parts),len(cand),4)
            score=.65*first+.35*SequenceMatcher(None," ".join(parts[:tail])," ".join(cand[:tail])).ratio()
        if syntax: score=max(score,.85*SequenceMatcher(None," ".join(parts[:4])," ".join(syntax.split()[:4])).ratio())
        if score>best_score: best_item,best_score=item,score
    return best_item,best_score
def detect_context(line,ctx):
    low=norm(line)
    if low.startswith("interface "): return {"view":"interface","name":line.strip().split(None,1)[1]}
    if low.startswith("vlan ") and re.match(r"^vlan\s+\d+",low): return {"view":"vlan","name":line.strip().split(None,1)[1]}
    if low.startswith("ospf "): return {"view":"ospf","name":line.strip().split(None,1)[1]}
    if low.startswith("acl "): return {"view":"acl","name":line.strip().split(None,1)[1]}
    if low in ("quit","return"): return {}
    return dict(ctx)
def context_label(ctx): return (f"{ctx.get('view')} · {ctx.get('name','')}" if ctx else "系统/全局视图").strip(" ·")
def context_applicability(line,item,ctx):
    cmd=norm(item.get("command","")) if item else ""
    interface_only=cmd.startswith(("port ","ip address","undo ip address","shutdown","undo shutdown"))
    if interface_only and ctx.get("view")!="interface":
        return {"level":"warning","message":"命令可能不在接口视图中","reason":"该命令通常需要在 interface 视图下执行。","suggest":"先执行 interface <接口名>，再配置当前命令。"}
    return None
def analyze_config(config):
    kb=load_kb(); results=[]; context={}; spelling=[]
    for line_no,raw in enumerate(config.splitlines(),1):
        line=raw.strip()
        if not line or line.startswith("#"): continue
        context=detect_context(line,context); exact=next((x for x in kb if command_match(line,x)),None)
        if not exact:
            n=norm(line)
            for cmd,info in COMMAND_DB.items():
                c=norm(cmd)
                if n==c or n.startswith(c+" "):
                    exact={"id":"legacy-"+cmd,"command":cmd,"module":info.get("category","其他"),"syntax":cmd,"description":info.get("explanation",""),"parameters":[],"scenes":info.get("scenario",""),"example":"","errors":info.get("common_errors",[]),"troubleshooting":[info.get("troubleshooting","")] if info.get("troubleshooting") else [],"related_commands":info.get("related_commands",[])}
                    break
        base={"line":line_no,"command":line,"context":context_label(context),"context_raw":dict(context),"recognized":False,"module":"Unknown","type":"未知命令","level":"warning","message":"未匹配到知识库命令","reason":"当前命令没有找到可靠的标准命令匹配，可能是拼写错误、参数格式问题或知识库尚未收录。","suggest":"检查命令拼写和参数；如为设备特有命令，可补充到知识库。","knowledge":None}
        if exact:
            base.update({"recognized":True,"module":exact.get("module","其他"),"type":"命令识别","level":"info","message":f"已识别：{exact.get('command','')}","reason":exact.get("description",""),"suggest":"","knowledge":exact})
            issue=context_applicability(line,exact,context)
            if issue: base.update({"recognized":True,"type":"上下文检查",**issue})
        else:
            candidate,score=fuzzy_match(line,kb)
            if candidate and score>=.72:
                correct=candidate.get("syntax") or candidate.get("command")
                base.update({"module":candidate.get("module","其他"),"type":"命令拼写错误","message":f"第{line_no}行疑似命令拼写错误","reason":f"与知识库标准命令相似度较高（{score:.0%}），可能存在关键字拼写或格式错误。","suggest":f"修改为：{correct}","knowledge":candidate,"match_score":round(score,3)})
                spelling.append({"line":line_no,"original":line,"suggestion":correct,"module":candidate.get("module","其他"),"score":round(score,3)})
        results.append(base)
    return results
def search_commands(q,limit=20):
    q=norm(q)
    if not q:return []
    rows=[]
    for item in load_kb():
        text=" ".join(str(item.get(k,"")) for k in ("command","syntax","module","description","scenes")).lower()
        if q in text:
            score=(100 if norm(item.get("command","")).startswith(q) else 0)+(50 if q in norm(item.get("syntax","")) else 0)+(20 if q in norm(item.get("module","")) else 0)
            rows.append((score,item))
    rows.sort(key=lambda x:x[0],reverse=True); return [x[1] for x in rows[:limit]]
def autocomplete(q,limit=10):
    q=norm(q)
    if not q:return []
    vals=[]
    for item in load_kb():
        for v in (item.get("syntax",""),item.get("command","")):
            if v and norm(v).startswith(q): vals.append(v)
    return list(dict.fromkeys(vals))[:limit]
def command_detail(command):
    n=norm(command)
    for item in load_kb():
        if norm(item.get("command",""))==n or norm(item.get("syntax",""))==n:return item
    return None

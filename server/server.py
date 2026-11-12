#!/usr/bin/python3
import json,os,re,sqlite3,subprocess,sys
from pathlib import Path
URI='ui://recent-chats/index.html'
HERE=Path(__file__).resolve().parent
DB=Path.home()/'.codex/state_5.sqlite'
META={'ui':{'resourceUri':URI},'openai/ui':{'entrypoints':[{'type':'global'}]}}
SCHEMA={'type':'object','properties':{},'additionalProperties':False}
TOOLS=[{'name':'recent_chats','title':'最近对话','description':'查看和搜索最近的本机 Codex 对话。','inputSchema':SCHEMA,'annotations':{'readOnlyHint':True},'_meta':META},{'name':'list_recent_chats','description':'读取最近 200 条本机 Codex 聊天。','inputSchema':SCHEMA,'annotations':{'readOnlyHint':True},'_meta':{'ui':{'visibility':['app']}}},{'name':'open_chat','description':'打开用户在列表中选定的本机 Codex 聊天。','inputSchema':{'type':'object','properties':{'id':{'type':'string'}},'required':['id'],'additionalProperties':False},'_meta':{'ui':{'visibility':['app']}}}]
def chats():
 con=sqlite3.connect(f'file:{DB}?mode=ro',uri=True,timeout=1)
 try:
  rows=con.execute("""SELECT id,COALESCE(NULLIF(name,''),NULLIF(title,''),'未命名对话'),cwd,CASE WHEN recency_at_ms>0 THEN recency_at_ms ELSE updated_at_ms END FROM threads WHERE archived=0 AND preview<>'' AND source='vscode' AND COALESCE(thread_source,'user') IN ('user','chatgpt_handoff','agent_created_thread') AND attached_thread_parent_id IS NULL ORDER BY 4 DESC,id DESC LIMIT 200""").fetchall()
  return [{'id':i,'title':' '.join(t.split()),'folder':os.path.basename(c) or '未分类','time':ms} for i,t,c,ms in rows]
 finally:con.close()
def handle(req):
 method=req.get('method');p=req.get('params') or {}
 if method=='initialize':return {'protocolVersion':p.get('protocolVersion','2025-03-26'),'capabilities':{'tools':{},'resources':{},'extensions':{'io.modelcontextprotocol/ui':{}}},'serverInfo':{'name':'recent-chats','version':'1.3.0'}}
 if method=='ping':return {}
 if method=='tools/list':return {'tools':TOOLS}
 if method=='resources/list':return {'resources':[{'uri':URI,'name':'最近对话','mimeType':'text/html;profile=mcp-app'}]}
 if method=='resources/templates/list':return {'resourceTemplates':[]}
 if method=='resources/read':
  if p.get('uri')!=URI:raise ValueError('Unknown resource')
  return {'contents':[{'uri':URI,'mimeType':'text/html;profile=mcp-app','text':(HERE/'index.html').read_text()}]}
 if method=='tools/call':
  name=p.get('name');args=p.get('arguments') or {}
  if name in ('recent_chats','list_recent_chats'):return {'content':[{'type':'text','text':'已读取本机最近对话。'}],'structuredContent':{'chats':chats()}}
  if name=='open_chat':
   i=args.get('id','')
   if not re.fullmatch(r'[0-9a-fA-F-]{36}',i) or not any(c['id']==i for c in chats()):return {'isError':True,'content':[{'type':'text','text':'找不到此聊天，请刷新。'}]}
   result=subprocess.run(['/usr/bin/open','codex://threads/'+i],capture_output=True,text=True,timeout=10)
   return {'isError':result.returncode!=0,'content':[{'type':'text','text':'已请求打开聊天。' if result.returncode==0 else '无法打开聊天。'}]}
  raise ValueError('Unknown tool')
 raise ValueError('Unknown method')
for line in sys.stdin:
 try:
  req=json.loads(line)
  if 'id' not in req:continue
  try:r={'jsonrpc':'2.0','id':req['id'],'result':handle(req)}
  except Exception as e:r={'jsonrpc':'2.0','id':req['id'],'error':{'code':-32603,'message':str(e)}}
  print(json.dumps(r,ensure_ascii=False),flush=True)
 except Exception:continue

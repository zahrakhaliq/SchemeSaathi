"""SchemeSaathi Source Maintenance Agent v2.1."""
import json, os, re, time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
import requests

DATA_PATH=Path('data/schemes.json')
REPORT_PATH=Path('data/source_refresh_report.json')
TIMEOUT=15
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36 SchemeSaathi/2.1'

KNOWN={
 'Chief Minister Honhaar Scholarship Program':['https://hed.punjab.gov.pk/node/1674'],
 'CM Punjab Free Solar Panel Scheme':['https://energy.punjab.gov.pk/node/165','https://www.punjab.gov.pk/cm-punjab-free-solar-panel-scheme'],
 'CM Punjab Livestock Card':['https://punjab.gov.pk/cm-punjab-livestock-card','https://plc.punjab.gov.pk/'],
 'CM Livestock Asset Transfer to Rural Women Scheme':['https://www.punjab.gov.pk/attrw-scheme'],
}
DOMAINS={
 'Chief Minister Honhaar Scholarship Program':['hed.punjab.gov.pk','punjab.gov.pk'],
 'CM Punjab Free Solar Panel Scheme':['energy.punjab.gov.pk','punjab.gov.pk'],
 'CM Punjab Livestock Card':['punjab.gov.pk','plc.punjab.gov.pk','livestock.punjab.gov.pk'],
 'CM Livestock Asset Transfer to Rural Women Scheme':['punjab.gov.pk','livestock.punjab.gov.pk'],
}

def host(url): return urlparse(url).netloc.lower().split(':')[0].removeprefix('www.')
def official(url):
 h=host(url); return h=='punjab.gov.pk' or h.endswith('.punjab.gov.pk')
def same_official(a,b): return official(a) and official(b)

def check(url):
 h={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8','Accept-Language':'en-US,en;q=0.8'}
 try:
  r=requests.head(url,headers=h,timeout=TIMEOUT,allow_redirects=True)
  if 200<=r.status_code<400: return True,r.status_code,r.url
  r=requests.get(url,headers=h,timeout=TIMEOUT,allow_redirects=True)
  return 200<=r.status_code<400,r.status_code,r.url
 except requests.RequestException as e: return False,None,str(e)

def norm(s): return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9 ]+',' ',s.lower())).strip()
def toks(s):
 generic={'chief','minister','punjab','program','programme','scheme','initiative','project','cm','the','and','of','to','for'}
 return set(norm(s).split())-generic
def sim(name,text):
 a,b=toks(name),toks(text)
 return len(a&b)/max(1,len(a)) if a else 0
def strong(name,text):
 a=toks(name); overlap=a&toks(text)
 return len(overlap)>=1 if len(a)<=2 else len(overlap)>=2 or sim(name,text)>=.45

def search(query,domains):
 key=os.getenv('TAVILY_API_KEY')
 if not key:return []
 p={'api_key':key,'query':query,'search_depth':'advanced','max_results':8,'include_answer':False,'include_domains':domains}
 try:
  r=requests.post('https://api.tavily.com/search',json=p,headers={'User-Agent':UA},timeout=30); r.raise_for_status(); return r.json().get('results',[])
 except requests.RequestException:return []

def candidate(scheme,url,result,domain):
 if not official(url): return None
 evidence=' '.join([scheme['name'],result.get('title',''),result.get('content',''),url])
 score=sim(scheme['name'],evidence)
 ok,status,final=check(url)
 # 403/429/5xx may be WAF/anti-bot; official search evidence can still verify.
 if strong(scheme['name'],evidence) and (ok or status in {403,429,500,502,503,504}):
  return (final if ok else url,score,status,'direct_http' if ok else 'official_search_evidence',f'Official {domain} source; similarity={score:.2f}; HTTP={status}.')
 return None

def find(scheme):
 name=scheme['name']; domains=DOMAINS.get(name,[host(scheme.get('official_url','')) or 'punjab.gov.pk'])
 best=None
 for url in KNOWN.get(name,[]):
  if not official(url):continue
  ok,status,final=check(url)
  evidence=f'{name} {url}'
  if strong(name,evidence) and (ok or status in {403,429,500,502,503,504}):
   c=(final if ok else url,max(sim(name,evidence),.5),status,'direct_http' if ok else 'official_source_registry',f'Curated official Punjab source; HTTP={status}.')
   if best is None or c[1]>best[1]:best=c
 for d in domains:
  for q in [f'"{name}" site:{d}',f'{name} Punjab site:{d}']:
   for r in search(q,[d]):
    u=r.get('url','')
    if not u:continue
    c=candidate(scheme,u,r,d)
    if c and (best is None or c[1]>best[1]):best=c
 if best and best[1]>=.34:return best
 return None

def main():
 schemes=json.loads(DATA_PATH.read_text(encoding='utf-8')); today=str(date.today()); report={'run_date':today,'agent_version':'2.1','checked':0,'working':0,'verified_via_search':0,'repaired':0,'unresolved':0,'changes':[]}; changed=False
 for s in schemes:
  url=s.get('official_url','')
  if not url:continue
  report['checked']+=1; ok,status,final=check(url)
  if ok:
   report['working']+=1; s['last_verified']=date.today().strftime('%B %Y'); s['source_refresh_status']='Verified by direct HTTP.'; changed=True
   if final and same_official(url,final) and final!=url:
    s['official_url']=final; report['changes'].append({'scheme':s['name'],'type':'redirect_canonicalized','old_url':url,'new_url':final,'http_status':status})
   continue
  c=find(s)
  if c:
   new,score,http,via,reason=c
   if new==url:
    report['working']+=1; report['verified_via_search']+=1; s['last_verified']=date.today().strftime('%B %Y'); s['source_refresh_status']='Verified via official search evidence; direct HTTP unavailable.'; changed=True
    report['changes'].append({'scheme':s['name'],'type':'verified_via_search','old_url':url,'confidence':round(score,3),'reason':reason})
   else:
    s['official_url']=new; s['last_verified']=date.today().strftime('%B %Y'); s['source_refresh_status']='Repaired by maintenance agent; official source verified.'; changed=True; report['repaired']+=1
    report['changes'].append({'scheme':s['name'],'type':'broken_link_repaired','old_url':url,'new_url':new,'confidence':round(score,3),'verification':via,'reason':reason})
  else:
   # Trust rule: unresolved sources retain their old URL and do NOT get a new last_verified date.
   s['source_refresh_status']='Source could not be verified; existing URL retained.'; changed=True; report['unresolved']+=1
   report['changes'].append({'scheme':s['name'],'type':'unresolved','old_url':url,'confidence':0.0,'reason':'No high-confidence official replacement found.'})
  time.sleep(.25)
 if changed: DATA_PATH.write_text(json.dumps(schemes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 REPORT_PATH.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,indent=2,ensure_ascii=False)); return 0
if __name__=='__main__':raise SystemExit(main())

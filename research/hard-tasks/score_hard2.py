import json,subprocess,sys,re,os
R="<WORKDIR>/hard2-runs"; H=os.path.dirname(os.path.abspath(__file__)); BASE="<WORKDIR>/p1-base"
def cost(f):
    c=0
    for l in open(f,encoding="utf-8",errors="replace"):
        try:e=json.loads(l)
        except ValueError:continue
        if e.get("type")=="result":c=e.get("total_cost_usd") or 0
    return c
def check(task,d):
    if task=="cache": cmd=[sys.executable,"-I",f"{H}/hidden_cache.py",f"{d}/sfcache.py"]
    elif task=="ml": cmd=[sys.executable,f"{H}/hidden_ml.py",d]
    elif task=="ladder": cmd=[sys.executable,"-I",f"{H}/hidden_ladder.py",d]
    elif task=="refactor": cmd=[sys.executable,"-I",f"{H}/hidden_refactor.py",d,BASE]
    else: cmd=[sys.executable,"-I",f"{H}/hidden_plugin.py",d,BASE]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=900); out=r.stdout+r.stderr
    p=len(re.findall(r"^\s*(PASS|ok|OK)\b",out,re.M)); f=len(re.findall(r"^\s*(FAIL|fail)\b",out,re.M))
    return out.strip().splitlines()[-1][:80] if out.strip() else "no output", p, f
for task in sys.argv[1].split(","):
    for arm in sys.argv[2].split(","):
        d=f"{R}/{task}-{arm}"
        if not os.path.isdir(d): continue
        try: last,p,f=check(task,d)
        except Exception as ex: last,p,f=str(ex)[:60],0,0
        print(f"{task:9}{arm:8} ${cost(f'{H}/{task}-{arm}.jsonl'):.2f}  {last}")

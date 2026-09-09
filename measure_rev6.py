#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,os,re,shlex,signal,statistics,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results'
THEORIES=ROOT/'theories'
TRANSPORT='theories/ibcv2_transport_nat.spthy'
P4DIAG='theories/ibcv2_p4_nat_diagnostic.spthy'
ICS20='theories/ibcv2_ics20_projection.spthy'
SUITES={
 'smoke-transport':[(TRANSPORT,x) for x in ['P1_AuthenticDelivery','P2_ExactlyOnceReceipt','P3_AckCorrespondence','ReceiptBeforeHeight','WitnessBeforeReceiptHeight','P4_TimeoutSafety','P5_ClientPortBinding']],
 'p4':[(TRANSPORT,x) for x in ['ReceiptBeforeHeight','WitnessBeforeReceiptHeight','P4_TimeoutSafety']],
 'p4diag':[(P4DIAG,'P4_TimeoutSafety_NoHelpers')],
 'sanity-transport':[(TRANSPORT,x) for x in ['ExecutableRecv','ExecutableAck','ExecutableTimeout']],
 'smoke-p6':[(ICS20,x) for x in ['P6_MintImpliesLock','P6_RefundImpliesLock','P6_NoDoubleMint','P6_NoMintAndRefund']],
 'sanity-p6':[(ICS20,x) for x in ['ExecutableICS20Mint','ExecutableICS20Refund']],
 'proofs':[(TRANSPORT,x) for x in ['P1_AuthenticDelivery','P2_ExactlyOnceReceipt','P3_AckCorrespondence','ReceiptBeforeHeight','WitnessBeforeReceiptHeight','P4_TimeoutSafety','P5_ClientPortBinding']]+[(ICS20,x) for x in ['P6_MintImpliesLock','P6_RefundImpliesLock','P6_NoDoubleMint','P6_NoMintAndRefund']],
}
RESULT_RE=re.compile(r'^\s*(?P<name>[A-Za-z0-9_]+)\s*\([^)]*\):\s*(?P<outcome>verified|falsified|analysis incomplete|inconclusive)(?:\s*\((?P<steps>\d+)\s+steps?\))?',re.I|re.M)
RSS_RE=re.compile(r'maxrss_kb=(?P<rss>\d+)')
def run_text(cmd,timeout=30):
 try:return subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout).stdout.strip()
 except Exception as e:return f'<unavailable: {e}>'
def sha256(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def env(tam,threads,heap,out):
 lines=[f'timestamp={dt.datetime.now().astimezone().isoformat(timespec="seconds")}',f'cwd={ROOT}',f'tamarin_command={tam}',f'tamarin_version={run_text([tam,"-V"])}',f'maude_version={run_text(["maude","--version"])}',f'python={sys.version.replace(os.linesep," ")}',f'threads_fixed={threads}',f'heap_cap_gb={heap}',f'uname={run_text(["uname","-a"])}',f'memory={run_text(["free","-h"])}']
 for n in [TRANSPORT,P4DIAG,ICS20,'measure_rev6.py','Makefile']:
  p=ROOT/n
  if p.exists():lines.append(f'sha256[{n}]={sha256(p)}')
 (out/'environment.txt').write_text('\n\n'.join(lines)+'\n')
def warm(tam,theories,threads,heap):
 for th in sorted(set(theories)):
  cmd=[tam,'--parse-only',str(ROOT/th),'+RTS',f'-N{threads}',f'-M{heap}G','-RTS'];print('WARM:',shlex.join(cmd),flush=True)
  p=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  if p.returncode:sys.stderr.write(p.stdout);raise SystemExit(f'parse failed: {th}')
def one(tam,theory,lemma,run,threads,heap,timeout_s,out):
 safe=f'{Path(theory).stem}__{lemma}__run{run}__N{threads}';log=out/f'{safe}.log';tm=out/f'{safe}.time'
 cmd0=[tam]
 if lemma.startswith('Executable'):cmd0+=['--stop-on-trace=BFS']
 cmd0 += [f'--prove={lemma}',str(ROOT/theory),'+RTS',f'-N{threads}',f'-M{heap}G','-RTS']
 cmd=['/usr/bin/time','-f','maxrss_kb=%M','-o',str(tm)]+cmd0
 print(f'RUN {run}: {theory} :: {lemma}',flush=True);print(' ',shlex.join(cmd),flush=True)
 st=time.perf_counter();to=False
 with log.open('w') as f:
  p=subprocess.Popen(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,text=True,start_new_session=True)
  try:rc=p.wait(timeout=timeout_s)
  except subprocess.TimeoutExpired:
   to=True
   try:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
   except Exception:
    try:os.killpg(p.pid,signal.SIGKILL)
    except Exception:pass
   rc=124
 wall=time.perf_counter()-st;txt=log.read_text(errors='replace');ms=[m for m in RESULT_RE.finditer(txt) if m.group('name')==lemma]
 if ms:m=ms[-1];outcome=m.group('outcome').lower();steps=m.group('steps') or ''
 elif to:outcome,steps='timeout',''
 elif rc:outcome,steps='error',''
 else:outcome,steps='unparsed',''
 rss=''
 if tm.exists():
  mm=RSS_RE.search(tm.read_text(errors='replace'))
  if mm:rss=int(mm.group('rss'))
 return dict(theory=theory,lemma=lemma,run=run,threads=threads,heap_gb=heap,timeout_s=timeout_s,exit_code=rc,outcome=outcome,steps=steps,wall_s_monotonic=round(wall,6),maxrss_kb=rss,timed_out=to,search='BFS' if lemma.startswith('Executable') else 'default',log=log.name)
def write(rows,out):
 flds=['theory','lemma','run','threads','heap_gb','timeout_s','exit_code','outcome','steps','wall_s_monotonic','maxrss_kb','timed_out','search','log']
 with (out/'runs.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=flds);w.writeheader();w.writerows(rows)
 groups={}
 for r in rows:groups.setdefault((r['theory'],r['lemma']),[]).append(r)
 sm=[]
 for (th,lm),g in groups.items():
  ok=[r for r in g if r['outcome'] in {'verified','falsified'}];outs=[r['outcome'] for r in g]
  sm.append(dict(theory=th,lemma=lm,runs=len(g),outcome=outs[0] if len(set(outs))==1 else 'MIXED:'+ '/'.join(outs),median_steps=statistics.median([int(r['steps']) for r in ok if r['steps']!='']) if any(r['steps']!='' for r in ok) else '',median_wall_s_monotonic=statistics.median([r['wall_s_monotonic'] for r in ok]) if ok else '',median_maxrss_kb=statistics.median([int(r['maxrss_kb']) for r in ok if r['maxrss_kb']!='']) if any(r['maxrss_kb']!='' for r in ok) else ''))
 sf=['theory','lemma','runs','outcome','median_steps','median_wall_s_monotonic','median_maxrss_kb']
 with (out/'summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=sf);w.writeheader();w.writerows(sm)
 lines=['# Tamarin rev6 modular measurement summary','','| Theory | Lemma | Runs | Outcome | Median steps | Median wall (s) | Median Max RSS (KB) |','|---|---|---:|---|---:|---:|---:|']
 for r in sm:lines.append(f"| {r['theory']} | {r['lemma']} | {r['runs']} | {r['outcome']} | {r['median_steps']} | {r['median_wall_s_monotonic']} | {r['median_maxrss_kb']} |")
 (out/'summary.md').write_text('\n'.join(lines)+'\n')
def main():
 a=argparse.ArgumentParser();a.add_argument('--suite',choices=sorted(SUITES),default='smoke-transport');a.add_argument('--runs',type=int,default=1);a.add_argument('--threads',type=int,default=1);a.add_argument('--heap-gb',type=int,default=8);a.add_argument('--timeout',type=int,default=1800);a.add_argument('--tamarin',default='tamarin-prover');a.add_argument('--tag',default='');x=a.parse_args();items=SUITES[x.suite];RESULTS.mkdir(exist_ok=True);od=RESULTS/(dt.datetime.now().strftime('%Y%m%d-%H%M%S')+f'-{x.suite}-N{x.threads}'+(f'-{x.tag}' if x.tag else ''));od.mkdir(parents=True);env(x.tamarin,x.threads,x.heap_gb,od);warm(x.tamarin,[t for t,_ in items],x.threads,x.heap_gb);rows=[]
 for rn in range(1,x.runs+1):
  for th,lm in items:rows.append(one(x.tamarin,th,lm,rn,x.threads,x.heap_gb,x.timeout,od));write(rows,od)
 print(f'RESULT_DIR={od}');print((od/'summary.md').read_text())
if __name__=='__main__':main()

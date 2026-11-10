"""Publication artwork from accepted saved tables. No new statistics or calls."""
from pathlib import Path
import os,csv,json,hashlib,collections
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CACHE=HERE/'.cache';CACHE.mkdir(exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR',str(CACHE));os.environ.setdefault('XDG_CACHE_HOME',str(CACHE))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
ART=ROOT/'paper/results_draft_v1/figures';ART.mkdir(exist_ok=True)
TABLES=ROOT/'reports/results_readiness_v1/tables'
MAIN='primary69__main'
COLORS={'RR':'#777777','SA':'#D55E00','EW':'#0072B2'}
STRATA=[('A','openai','Task A · GPT',35),('A','anthropic','Task A · Claude',35),('B','openai','Task B · GPT',34),('B','anthropic','Task B · Claude',34)]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8.7,'axes.titlesize':9.2,'axes.labelsize':8.7,'xtick.labelsize':8.2,'ytick.labelsize':8.7,'legend.fontsize':8.7,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.linewidth':.6,'axes.spines.top':False,'axes.spines.right':False,'grid.linewidth':.5,'grid.alpha':.28,'figure.facecolor':'white','savefig.facecolor':'white'})
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def get(rows,task,provider,**kw):
 rr=[r for r in rows if r['view']==MAIN and r['task']==task and r['provider']==provider and all(r[k]==v for k,v in kw.items())]
 assert len(rr)==1;return rr[0]
def clean(ax):
 ax.set_axisbelow(True);ax.grid(axis='x',color='#BFBFBF');ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0)
def pformat(s):
 x=float(s);exp=int(np.floor(np.log10(x)));m=x/(10**exp)
 return rf'${m:.2f}\times 10^{{{exp}}}$'
def export(fig,name,rows,sources):
 fig.canvas.draw()
 for ext in ['pdf','png','svg']:
  kw={'dpi':320} if ext=='png' else {}
  fig.savefig(ART/f'{name}.{ext}',**kw)
 keys=list(dict.fromkeys(k for row in rows for k in row))
 with (HERE/'data'/f'{name}.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
 (HERE/'data'/f'{name}.json').write_text(json.dumps({'sources':{str(p.relative_to(ROOT)):sha(p) for p in sources},'width_inches':fig.get_figwidth(),'height_inches':fig.get_figheight(),'rows':len(rows),'no_new_inference':True,'PDF':str((ART/f'{name}.pdf').relative_to(ROOT))},indent=2)+'\n')
 plt.close(fig)
def preservation():
 a=TABLES/'RQ2_core_preservation.csv';b=TABLES/'paired_main_and_alternative.csv';means=read(a);pairs=read(b)
 fig=plt.figure(figsize=(7.1,3.2));ax=fig.add_axes([.18,.185,.285,.64]);fx=fig.add_axes([.585,.185,.255,.64]);yy=np.arange(4)[::-1];rows=[]
 for i,(task,provider,label,n) in enumerate(STRATA):
  y=yy[i]
  for arm,off,marker in [('RR',.20,'s'),('SA',0,'^'),('EW',-.20,'o')]:
   r=get(means,task,provider,condition=arm);rows.append({'record':'condition_mean',**r});x=100*float(r['core_loss_rate_mean'])
   ax.scatter(x,y+off,color=COLORS[arm],marker=marker,s=24,zorder=3)
   ax.text(x+1.35,y+off,f'{x:.1f}',ha='left',va='center',color=COLORS[arm],fontsize=8.0)
  r=get(pairs,task,provider,metric='core_loss_rate',contrast='EW minus SA');rows.append({'record':'paired_effect',**r})
  effect=float(r['difference_percentage_points']);lo=float(r['ci_low_pp']);hi=float(r['ci_high_pp'])
  fx.errorbar(effect,y,xerr=[[effect-lo],[hi-effect]],fmt='D',color=COLORS['EW'],markersize=4.0,elinewidth=1.3,capsize=3,zorder=3)
  fx.text(effect,y+.21,f'{effect:.1f}',ha='center',va='center',color=COLORS['EW'],fontsize=8.2)
  fx.text(1.065,y,pformat(r['exact_holm_p']),transform=fx.get_yaxis_transform(),ha='left',va='center',fontsize=8.0)
 ax.set_yticks(yy,[f'{label}\n(n={n})' for _,_,label,n in STRATA]);ax.tick_params(axis='y',pad=7)
 ax.set_xlim(0,50);ax.set_xticks([0,10,20,30,40,50]);ax.set_xlabel('Prior core-test passes lost (%)')
 fx.set_yticks(yy,[]);fx.set_xlim(-40,4);fx.set_xticks([-40,-30,-20,-10,0]);fx.axvline(0,color='#555555',ls='--',lw=.8)
 fx.set_xlabel('EW − SA (percentage points)')
 for a1 in [ax,fx]:a1.set_ylim(-.5,3.6);clean(a1)
 ax.set_title('(a) Mean collateral regression',loc='left',pad=9,fontweight='bold',fontsize=8.8)
 fx.set_title('(b) Paired difference',loc='left',pad=9,fontweight='bold',fontsize=8.8)
 fx.text(1.065,1.06,'Adjusted $p$',transform=fx.transAxes,ha='left',va='bottom',fontsize=8.0)
 fig.legend(handles=[Line2D([],[],ls='',color=COLORS[x],marker=m,label=x,markersize=5) for x,m in [('RR','s'),('SA','^'),('EW','o')]],loc='upper left',bbox_to_anchor=(.17,.995),ncol=3,frameon=False,columnspacing=.8,handletextpad=.4)
 export(fig,'preservation_effects',rows,[a,b])
def offsets(values,step=.065):
 by=collections.defaultdict(list);out=np.zeros(len(values))
 for i,v in enumerate(values):by[round(v,10)].append(i)
 for ids in by.values():
  for j,i in enumerate(ids):out[i]=(j-(len(ids)-1)/2)*step
 return out

def groups():
 p=ROOT/'reports/full_analysis_v2_prelim/tables/session_metrics.csv';base=TABLES/'RQ4_group_baselines.csv';sessions=[r for r in read(p) if r['view']==MAIN];baseline=read(base)
 assert len(sessions)==414
 fig,axs=plt.subplots(2,2,figsize=(7.1,4.05),sharex=True)
 fig.subplots_adjust(left=.085,right=.985,top=.855,bottom=.145,wspace=.26,hspace=.45)
 rows=[]
 for ax,(task,provider,label,n) in zip(axs.flat,STRATA):
  ax.set_title(label,loc='left',fontweight='bold',pad=6,fontsize=9.2)
  for j,g in enumerate(['G1','G2','G3']):
   bb=next(r for r in baseline if r['view']==MAIN and r['task']==task and r['group']==g)
   for arm,dy,marker in [('SA',-.14,'^'),('EW',.14,'o')]:
    rr=sorted([r for r in sessions if r['task']==task and r['provider']==provider and r['group']==g and r['condition']==arm],key=lambda r:r['participant_id'])
    vals=[100*float(r['core_loss_rate']) for r in rr];ofs=offsets(vals);zero=sum(v==0 for v in vals)
    for i,v in enumerate(vals):
     if v==0:ofs[i]=0
    y=2-j+dy;ax.scatter(vals,y+ofs,color=COLORS[arm],marker=marker,s=12,edgecolors='white',linewidths=.2,alpha=.8,zorder=3)
    if zero>1:ax.annotate(f'×{zero}',(0,y),xytext=(-3,0),textcoords='offset points',ha='right',va='center',fontsize=8.0,color=COLORS[arm],zorder=5,bbox={'facecolor':'white','edgecolor':'none','pad':.15})
    ax.scatter([np.mean(vals)],[y],marker='D',s=35,facecolor='white',edgecolor=COLORS[arm],linewidths=1.25,zorder=4)
    for r,v in zip(rr,vals):rows.append({'task':task,'provider':provider,'group':g,'condition':arm,'participant_id':r['participant_id'],'core_loss_percent':v,'group_n':len(rr),'baseline_pass_mean':bb['core_baseline_pass_mean']})
  ax.set_xlim(-9,103);ax.set_ylim(-.48,2.48);ax.set_xticks([0,25,50,75,100]);ax.set_yticks([2,1,0],['G1','G2','G3']);ax.tick_params(axis='y',pad=8);clean(ax)
  if task=='A':ax.tick_params(axis='x',labelbottom=False)
  else:ax.set_xlabel('Prior core-test passes lost (%)')
 handles=[Line2D([],[],color=COLORS[a],marker=m,ls='',label=a,markersize=5) for a,m in [('SA','^'),('EW','o')]]+[Line2D([],[],color='black',marker='D',markerfacecolor='white',ls='',label='Group mean',markersize=5)]
 fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.51,.995),ncol=3,frameon=False,columnspacing=1.6,handletextpad=.5)
 export(fig,'group_preservation',rows,[p,base])
if __name__=='__main__':
 preservation();groups();print('Built two publication figures from saved results')

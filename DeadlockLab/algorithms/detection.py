"""Deadlock detection, prevention policy, and recovery helpers."""
from copy import deepcopy


def detect_deadlock(cfg):
    processes=cfg['processes']; allocation=cfg['allocation']; request=cfg['request']; work=list(cfg['available'])
    # Standard multi-instance detection: zero-allocation processes may be marked finished initially.
    finish=[all(v==0 for v in row) for row in allocation]
    trace=[]; sequence=[]
    while True:
        found=None
        for i in range(len(processes)):
            if not finish[i] and all(request[i][j] <= work[j] for j in range(len(work))):
                found=i; break
        if found is None: break
        before=work[:]; work=[work[j]+allocation[found][j] for j in range(len(work))]
        finish[found]=True; sequence.append(processes[found])
        trace.append({'step':len(trace)+1,'process':processes[found],'request':request[found][:],'work_before':before,'released':allocation[found][:],'work_after':work[:]})
    return {'deadlocked':[processes[i] for i,v in enumerate(finish) if not v], 'sequence':sequence,'finish':finish,'work':work,'trace':trace}


def ordering_check(acquisition_sequence, resource_order):
    rank={name:i for i,name in enumerate(resource_order)}
    if any(name not in rank for name in acquisition_sequence): return {'valid':False,'reason':'Sequence contains an unknown resource.'}
    for a,b in zip(acquisition_sequence, acquisition_sequence[1:]):
        if rank[a] >= rank[b]: return {'valid':False,'reason':f'{b} must not be acquired after {a}; acquire resources in strictly increasing global order.'}
    return {'valid':True,'reason':'Acquisition follows the fixed global resource order.'}


def terminate_process(cfg, process_name):
    out=deepcopy(cfg)
    if process_name not in out['processes']: raise ValueError('Unknown process.')
    i=out['processes'].index(process_name)
    released=out['allocation'][i][:]
    out['available']=[x+y for x,y in zip(out['available'],released)]
    out['processes'].pop(i); out['allocation'].pop(i); out['request'].pop(i)
    return out,released

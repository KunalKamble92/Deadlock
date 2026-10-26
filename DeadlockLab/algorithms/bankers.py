"""Pure, testable Banker’s algorithm and request simulation functions."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def need_matrix(allocation: list[list[int]], maximum: list[list[int]]) -> list[list[int]]:
    if len(allocation) != len(maximum) or any(len(a) != len(m) for a, m in zip(allocation, maximum)):
        raise ValueError("Allocation and Maximum dimensions must match.")
    for i, (a, m) in enumerate(zip(allocation, maximum)):
        for j, (av, mv) in enumerate(zip(a, m)):
            if not isinstance(av, int) or isinstance(av, bool) or not isinstance(mv, int) or isinstance(mv, bool):
                raise ValueError("Resource quantities must be integers.")
            if av < 0 or mv < 0 or av > mv:
                raise ValueError(f"Invalid Allocation/Maximum at process row {i}, resource column {j}.")
    return [[m - a for a, m in zip(ar, mr)] for ar, mr in zip(allocation, maximum)]


def validate_configuration(cfg: dict[str, Any]) -> list[str]:
    errors=[]
    p=cfg.get('processes', []); r=cfg.get('resources', [])
    alloc=cfg.get('allocation', []); maximum=cfg.get('maximum', []); avail=cfg.get('available', [])
    if not p or not r: errors.append('Add at least one process and one resource type.')
    if len(set(p)) != len(p): errors.append('Process names must be unique.')
    if len(set(r)) != len(r): errors.append('Resource names must be unique.')
    if len(alloc)!=len(p) or len(maximum)!=len(p): errors.append('Allocation and Maximum need one row per process.')
    if len(avail)!=len(r): errors.append('Available must have one value per resource type.')
    if errors: return errors
    for i in range(len(p)):
        if len(alloc[i])!=len(r) or len(maximum[i])!=len(r):
            errors.append(f'Rows for {p[i]} must contain {len(r)} resource values.'); continue
        for j in range(len(r)):
            a,m=alloc[i][j],maximum[i][j]
            if not isinstance(a,int) or isinstance(a,bool) or not isinstance(m,int) or isinstance(m,bool) or a<0 or m<0:
                errors.append(f'{p[i]} / {r[j]} must use non-negative integer values.')
            elif a>m: errors.append(f'Allocation for {p[i]} exceeds Maximum for {r[j]}.')
    for j,v in enumerate(avail):
        if not isinstance(v,int) or isinstance(v,bool) or v<0: errors.append(f'Available {r[j]} must be a non-negative integer.')
    return errors


def safety_check(cfg: dict[str, Any]) -> dict[str, Any]:
    errors=validate_configuration(cfg)
    if errors: raise ValueError(' '.join(errors))
    processes=cfg['processes']; allocation=deepcopy(cfg['allocation']); available=list(cfg['available'])
    need=need_matrix(allocation,cfg['maximum']); work=available[:]; finish=[False]*len(processes)
    trace=[]; sequence=[]
    while True:
        eligible=[i for i in range(len(processes)) if not finish[i] and all(need[i][j] <= work[j] for j in range(len(work)))]
        if not eligible: break
        i=eligible[0]; before=work[:]
        work=[work[j]+allocation[i][j] for j in range(len(work))]
        finish[i]=True; sequence.append(processes[i])
        trace.append({'step':len(trace)+1,'process':processes[i],'work_before':before,'need':need[i][:], 'decision':'Can finish','released':allocation[i][:], 'work_after':work[:], 'finish':finish[:]})
    unfinished=[processes[i] for i,x in enumerate(finish) if not x]
    return {'safe':not unfinished,'sequence':sequence,'need':need,'initial_work':available,'final_work':work,'finish':finish,'unfinished':unfinished,'trace':trace}


def evaluate_request(cfg: dict[str, Any], process_name: str, request: list[int]) -> dict[str, Any]:
    errors=validate_configuration(cfg)
    if errors: return {'status':'invalid','reason':'Configuration is invalid: '+' '.join(errors)}
    if process_name not in cfg['processes']: return {'status':'invalid','reason':'The selected process does not exist.'}
    if not isinstance(request,list) or len(request)!=len(cfg['resources']) or any(not isinstance(x,int) or isinstance(x,bool) or x<0 for x in request):
        return {'status':'invalid','reason':'Enter one non-negative whole number for every resource type.'}
    i=cfg['processes'].index(process_name); need=need_matrix(cfg['allocation'],cfg['maximum'])[i]
    for j,x in enumerate(request):
        if x>need[j]: return {'status':'invalid','reason':f'Request for {cfg["resources"][j]} exceeds {process_name} remaining Need ({need[j]}).'}
    for j,x in enumerate(request):
        if x>cfg['available'][j]: return {'status':'deferred','reason':f'Request for {cfg["resources"][j]} exceeds Available ({cfg["available"][j]}). It is waiting/deferred; the system is unchanged.'}
    tentative=deepcopy(cfg)
    tentative['allocation'][i]=[x+y for x,y in zip(tentative['allocation'][i],request)]
    tentative['available']=[x-y for x,y in zip(tentative['available'],request)]
    safety=safety_check(tentative)
    if not safety['safe']:
        return {'status':'unsafe','reason':'The temporary allocation would leave an unsafe state. The original state is unchanged.','safety':safety,'snapshot':deepcopy(cfg)}
    return {'status':'grantable','reason':'The temporary allocation preserves a safe state. Commit only after explicit confirmation.','safety':safety,'snapshot':deepcopy(cfg),'configuration':tentative}

import copy
from algorithms import need_matrix, safety_check, evaluate_request, detect_deadlock, ordering_check, terminate_process

SAFE={'processes':['P0','P1','P2','P3','P4'],'resources':['A','B','C'],
'allocation':[[0,1,0],[2,0,0],[3,0,2],[2,1,1],[0,0,2]],
'maximum':[[7,5,3],[3,2,2],[9,0,2],[2,2,2],[4,3,3]],'available':[3,3,2]}

def test_need_and_safe_sequence():
    assert need_matrix(SAFE['allocation'],SAFE['maximum'])[1]==[1,2,2]
    result=safety_check(SAFE); assert result['safe'] and len(result['sequence'])==5
    work=SAFE['available'][:]
    for step in result['trace']:
        assert all(n<=w for n,w in zip(step['need'],step['work_before']))
        work=step['work_after']

def test_request_deferred_and_original_unchanged():
    original=copy.deepcopy(SAFE); out=evaluate_request(SAFE,'P0',[4,0,0])
    assert out['status']=='deferred' and SAFE==original

def test_grantable_request_is_tentative():
    out=evaluate_request(SAFE,'P1',[1,0,2]); assert out['status'] in {'grantable','unsafe'}
    assert SAFE['available']==[3,3,2]

def test_invalid_request():
    assert evaluate_request(SAFE,'P0',[-1,0,0])['status']=='invalid'
    assert evaluate_request(SAFE,'PX',[0,0,0])['status']=='invalid'

def test_deadlock_detection_and_recovery():
    cfg={'processes':['P0','P1'],'resources':['A','B'],'allocation':[[1,0],[0,1]],'request':[[0,1],[1,0]],'available':[0,0]}
    assert set(detect_deadlock(cfg)['deadlocked'])=={'P0','P1'}
    updated,released=terminate_process(cfg,'P0'); assert released==[1,0] and updated['available']==[1,0]
    assert detect_deadlock(updated)['deadlocked']==[]

def test_ordering_policy():
    assert ordering_check(['A','B','C'],['A','B','C'])['valid']
    assert not ordering_check(['B','A'],['A','B'])['valid']

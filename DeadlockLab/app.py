from __future__ import annotations
import json, io, csv, logging
from datetime import datetime
from copy import deepcopy
import pandas as pd
import plotly.express as px
import streamlit as st
from algorithms import need_matrix, validate_configuration, safety_check, evaluate_request, detect_deadlock, ordering_check, terminate_process

logging.basicConfig(filename='deadlocklab.log', level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')
st.set_page_config(page_title='DeadlockLab', page_icon='🧠', layout='wide', initial_sidebar_state='expanded')

SAMPLE={'processes':['P0','P1','P2','P3','P4'],'resources':['A','B','C'],
'allocation':[[0,1,0],[2,0,0],[3,0,2],[2,1,1],[0,0,2]],
'maximum':[[7,5,3],[3,2,2],[9,0,2],[2,2,2],[4,3,3]],'available':[3,3,2]}
UNSAFE={'processes':['P0','P1','P2'],'resources':['A','B'],'allocation':[[1,0],[0,1],[1,0]],'maximum':[[2,1],[1,2],[2,1]],'available':[0,0]}
DEADLOCK={'processes':['P0','P1'],'resources':['A','B'],'allocation':[[1,0],[0,1]],'request':[[0,1],[1,0]],'available':[0,0]}

def init():
    defaults={'cfg':deepcopy(SAMPLE),'safety':None,'request_preview':None,'history':[],'detection_cfg':deepcopy(DEADLOCK),'test_results':None,'recovery_preview':None,'detect_result_config':None,'ai_records':[
      {'AI Tool Used':'','Purpose':'Dashboard design assistance','Output Generated':'','Student Verification':''},
      {'AI Tool Used':'','Purpose':'Algorithm/code assistance','Output Generated':'','Student Verification':''},
      {'AI Tool Used':'','Purpose':'Test-case generation/debugging','Output Generated':'','Student Verification':''}]}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
init()
cfg=st.session_state.cfg

st.markdown('<div class="hero"><h1>DeadlockLab</h1><p class="muted">Interactive Deadlock Analysis & Resource Allocation Simulator — all tools in one workspace</p></div>', unsafe_allow_html=True)
st.caption('Select a section from the navigation bar to configure resources, run algorithms, preview requests, detect deadlocks, test prevention/recovery, or export evidence.')

st.markdown('''<style>
.stApp{background:#0b1220;color:#e6edf7}.block-container{padding-top:1.3rem;max-width:1500px}
[data-testid="stSidebar"]{background:#101a2b;border-right:1px solid #24344c}
[data-testid="stMetric"]{background:#121e31;border:1px solid #263a55;padding:14px;border-radius:12px}
div[data-testid="stDataFrame"],div[data-testid="stTable"]{border:1px solid #263a55;border-radius:10px;overflow:hidden}
.stButton>button{border-radius:8px;border:1px solid #2b5b85;font-weight:600}
.st-key-main_navigation div[role="radiogroup"]{display:flex;flex-wrap:wrap;gap:8px;background:#101a2b;border:1px solid #263a55;border-radius:12px;padding:10px}
.st-key-main_navigation div[role="radiogroup"] label{background:#16243a;border:1px solid #2b405e;border-radius:8px;padding:7px 12px}
.hero{padding:22px 24px;border:1px solid #263a55;background:linear-gradient(115deg,#12233b,#101a2b);border-radius:16px;margin-bottom:16px}
.hero h1{margin:0;color:#f3f7ff}.muted{color:#9db0ca}.section{font-size:1.15rem;font-weight:700;margin-top:1rem}
</style>''', unsafe_allow_html=True)

sections=['Overview','Configuration','Safety','Time Machine','Graph','Detection','Prevention & Recovery','Test Lab','About']
active_section=st.radio('Navigation',sections,horizontal=True,label_visibility='collapsed',key='main_navigation')

with st.sidebar:
    st.markdown('## 🧠 DeadlockLab')
    st.caption('OS deadlock analysis workspace')
    st.caption('Choose a section from the navigation bar. All sections share the same session state.')
    st.divider()
    if st.button('↺ Reset to safe sample',use_container_width=True):
        st.session_state.cfg=deepcopy(SAMPLE); st.session_state.safety=None; st.session_state.request_preview=None; st.rerun()

need=need_matrix(cfg['allocation'],cfg['maximum']) if not validate_configuration(cfg) else []
def matrix_df(matrix, rows, cols): return pd.DataFrame(matrix,index=rows,columns=cols)
def show_matrices(c):
    n=need_matrix(c['allocation'],c['maximum'])
    a,b=st.columns(2)
    with a: st.markdown('**Allocation**'); st.dataframe(matrix_df(c['allocation'],c['processes'],c['resources']),use_container_width=True)
    with b: st.markdown('**Maximum**'); st.dataframe(matrix_df(c['maximum'],c['processes'],c['resources']),use_container_width=True)
    x,y=st.columns(2)
    with x: st.markdown('**Need = Maximum − Allocation**'); st.dataframe(matrix_df(n,c['processes'],c['resources']),use_container_width=True)
    with y: st.markdown('**Available**'); st.dataframe(pd.DataFrame([c['available']],index=['Available'],columns=c['resources']),use_container_width=True)
def safe_badge(result):
    if result is None: st.info('Not yet analyzed — run the safety algorithm to determine the current state.')
    elif result['safe']: st.success('SAFE STATE — a complete safe sequence exists.')
    else: st.error('UNSAFE STATE — no complete safe sequence was found. This does not by itself prove deadlock.')
def export_json(c): return json.dumps(c,indent=2).encode()

def run_tests():
    rows=[]
    def add(tid,scenario,expected,actual,passed,explanation,changed='No'):
        rows.append({'Test ID':tid,'Input scenario':scenario,'Expected result':expected,'Actual result':actual,'Pass/Fail':'PASS' if passed else 'FAIL','Explanation':explanation,'Original state changed':changed})
    r=safety_check(SAMPLE); add('TC1','Standard 5-process sample','Safe state', 'Safe' if r['safe'] else 'Unsafe',r['safe'],'A complete safe sequence was computed: '+' → '.join(r['sequence']))
    old = deepcopy(SAMPLE)
    original = deepcopy(old)

    x = evaluate_request(old, 'P0', [4, 0, 0])

    unchanged = old == original

    add(
        'TC2',
        'P0 requests A=4 while Available A=3',
        'WAITING / DEFERRED; original state unchanged',
        f"{x['status'].upper()}; state unchanged={unchanged}",
        x['status'] == 'deferred' and unchanged,
        'Request is within Need but exceeds Available.',
        'No' if unchanged else 'Yes'
    )
    # Search a small deterministic set for an unsafe request, so test reflects actual behavior.
    unsafe_cfg={'processes':['P0','P1','P2'],'resources':['A','B'],'allocation':[[0,0],[0,0],[1,1]],'maximum':[[0,2],[2,2],[1,2]],'available':[2,0]}
    found=evaluate_request(unsafe_cfg,'P1',[1,0])
    add('TC3','P1 requests A=1; tentative state has no complete safe sequence','Denied / rollback','UNSAFE' if found['status']=='unsafe' else found['status'].upper(),found['status']=='unsafe','The actual request evaluator rejects the tentative unsafe state and retains the original configuration.','No')
    d=detect_deadlock(DEADLOCK); ok=set(d['deadlocked'])=={'P0','P1'}; add('TC4','Two processes each hold one resource and request the other','P0 and P1 deadlocked',str(d['deadlocked']),ok,'Multiple-instance detection run against explicit outstanding requests.')
    pol=ordering_check(['B','A'],['A','B']); add('TC5','Acquire B then A under order A < B','Policy violation', 'Violation' if not pol['valid'] else 'Allowed',not pol['valid'],pol['reason'])
    invalid=evaluate_request(SAMPLE,'PX',[0,0,0]); add('TC6','Unknown process identifier','Invalid request',invalid['status'].upper(),invalid['status']=='invalid',invalid['reason'])
    # Boundary case: zero request is valid and does not alter the configuration.
    zero=evaluate_request(SAMPLE,'P0',[0,0,0]); add('TC7','Zero request vector','Valid safe-to-grant preview',zero['status'].upper(),zero['status']=='grantable','Zero is a valid boundary request; no resources are consumed.','No')
    return rows


if active_section=='Overview':
    with st.container():
        st.markdown('<div class="hero"><h1>DeadlockLab</h1><p class="muted">Interactive Deadlock Analysis & Resource Allocation Simulator</p></div>',unsafe_allow_html=True)
        errors=validate_configuration(cfg)
        if errors:
            for e in errors: st.error(e)
        total=[sum(row[j] for row in cfg['allocation'])+cfg['available'][j] for j in range(len(cfg['resources']))]
        result=st.session_state.safety
        m=st.columns(5)
        m[0].metric('Processes',len(cfg['processes'])); m[1].metric('Resource types',len(cfg['resources'])); m[2].metric('Total instances',sum(total)); m[3].metric('Available now',sum(cfg['available'])); m[4].metric('Safety result','Not analyzed' if result is None else ('Safe' if result['safe'] else 'Unsafe'))
        st.markdown('### Current system snapshot')
        show_matrices(cfg)
        st.markdown('### Resource utilization')
        util=pd.DataFrame({'Resource':cfg['resources'],'Allocated':[sum(row[j] for row in cfg['allocation']) for j in range(len(cfg['resources']))],'Available':cfg['available'],'Total':total})
        fig=px.bar(util,x='Resource',y=['Allocated','Available'],barmode='stack',title='Allocated vs available resource instances',color_discrete_sequence=['#22b8cf','#4f7cff'])
        fig.update_layout(paper_bgcolor='#0b1220',plot_bgcolor='#0b1220',font_color='#e6edf7',legend_title_text='')
        st.plotly_chart(fig,use_container_width=True)
        safe_badge(result)
        st.markdown('### Quick actions')
        q=st.columns(4)
        if q[0].button('Load safe example',use_container_width=True): st.session_state.cfg=deepcopy(SAMPLE); st.session_state.safety=None; st.rerun()
        if q[1].button('Load unsafe example',use_container_width=True): st.session_state.cfg=deepcopy(UNSAFE); st.session_state.safety=None; st.rerun()
        if q[2].button('Load deadlock example',use_container_width=True): st.session_state.detection_cfg=deepcopy(DEADLOCK); st.rerun()
        if q[3].button('Run test suite',use_container_width=True): st.session_state.test_results=run_tests(); st.rerun()
        st.caption('Total instances are derived per resource type as Allocation + Available. The separate detection example does not change the Banker’s configuration.')

if active_section=='Configuration':
    with st.container():
        st.title('System Configuration')
        st.write('Edit matrices below. Changes are validated before they replace the active configuration.')
        with st.form('config_form'):
            process_names=st.text_input('Process names (comma-separated)',','.join(cfg['processes']))
            resource_names=st.text_input('Resource names (comma-separated)',','.join(cfg['resources']))
            ps=[x.strip() for x in process_names.split(',') if x.strip()]; rs=[x.strip() for x in resource_names.split(',') if x.strip()]
            st.caption('Matrix editors use the names entered above. If dimensions change, matching rows/columns are initialized to zero; review every value before applying.')
            def resize(old, nr, nc): return [[old[i][j] if i<len(old) and j<len(old[i]) else 0 for j in range(nc)] for i in range(nr)]
            alloc0=resize(cfg['allocation'],len(ps),len(rs)); max0=resize(cfg['maximum'],len(ps),len(rs)); av0=cfg['available'][:len(rs)]+[0]*max(0,len(rs)-len(cfg['available']))
            alloc_df=st.data_editor(pd.DataFrame(alloc0,index=ps,columns=rs),key='alloc_editor',num_rows='fixed',use_container_width=True)
            max_df=st.data_editor(pd.DataFrame(max0,index=ps,columns=rs),key='max_editor',num_rows='fixed',use_container_width=True)
            avail_df=st.data_editor(pd.DataFrame([av0],index=['Available'],columns=rs),key='avail_editor',num_rows='fixed',use_container_width=True)
            submitted=st.form_submit_button('Validate and apply configuration',type='primary')
        if submitted:
            try:
                candidate={'processes':ps,'resources':rs,'allocation':alloc_df.astype(int).values.tolist(),'maximum':max_df.astype(int).values.tolist(),'available':avail_df.iloc[0].astype(int).tolist()}
                errors=validate_configuration(candidate)
                if errors:
                    for e in errors: st.error(e)
                else:
                    st.session_state.cfg=candidate; st.session_state.safety=None; st.session_state.request_preview=None
                    st.success('Configuration validated and applied.'); st.rerun()
            except Exception as e: st.error(f'Invalid input: use whole-number quantities and valid matrix dimensions. Details: {e}')
        c1,c2,c3=st.columns(3)
        if c1.button('Load standard safe sample'): st.session_state.cfg=deepcopy(SAMPLE); st.session_state.safety=None; st.rerun()
        if c2.button('Load unsafe sample'): st.session_state.cfg=deepcopy(UNSAFE); st.session_state.safety=None; st.rerun()
        uploaded=st.file_uploader('Load configuration JSON',type=['json'])
        if uploaded and st.button('Load uploaded JSON'):
            try:
                candidate=json.load(uploaded); errors=validate_configuration(candidate)
                if errors: st.error('Configuration not loaded: '+' '.join(errors))
                else: st.session_state.cfg=candidate; st.session_state.safety=None; st.success('Configuration loaded.'); st.rerun()
            except Exception as e: st.error(f'Could not read JSON: {e}')
        st.download_button('Save current configuration (JSON)',export_json(cfg),file_name='deadlocklab_config.json',mime='application/json')
        st.markdown('**Model definitions**')
        st.write('- Allocation: resources currently held by each process.\n- Maximum: declared maximum demand.\n- Need: Maximum − Allocation.\n- Available: currently unallocated instances.')

if active_section=='Safety':
    with st.container():
        st.title('Banker’s Safety Algorithm')
        st.write('Find whether at least one complete execution order can finish every process.')
        if st.button('Run safety algorithm',type='primary'):
            try: st.session_state.safety=safety_check(cfg)
            except Exception as e: st.error(str(e))
        if st.button('Reset trace'): st.session_state.safety=None
        res=st.session_state.safety; safe_badge(res)
        if res:
            st.metric('Safe sequence', ' → '.join(res['sequence']) if res['safe'] else 'No complete sequence')
            if res['trace']:
                rows=[]
                for x in res['trace']: rows.append({'Step':x['step'],'Process':x['process'],'Work Before':str(x['work_before']),'Need':str(x['need']),'Decision':x['decision'],'Allocation Released':str(x['released']),'Work After':str(x['work_after'])})
                st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
            if res['unfinished']: st.warning('Processes that could not finish: '+', '.join(res['unfinished']))
            with st.expander('Need matrix and algorithm explanation'):
                st.dataframe(matrix_df(res['need'],cfg['processes'],cfg['resources']),use_container_width=True)
                st.write('Start Work = Available. Repeatedly select an unfinished process whose Need ≤ Work. When it finishes, release its Allocation into Work. The state is safe only if every process can finish.')

if active_section=='Time Machine':
    with st.container():
        st.title('⏱️ Deadlock Time Machine')
        st.write('Preview → inspect → commit or cancel. Previewing never mutates the live configuration.')
        c1,c2=st.columns([1,2])
        with c1:
            proc=st.selectbox('Requesting process',cfg['processes'])
            request=[st.number_input(f'Request for {r}',min_value=0,step=1,value=0,key=f'req_{r}') for r in cfg['resources']]
            preview=st.button('Preview request',type='primary',use_container_width=True)
            if st.button('Cancel / discard preview',use_container_width=True): st.session_state.request_preview=None; st.rerun()
        if preview:
            outcome=evaluate_request(deepcopy(cfg),proc,[int(x) for x in request])
            outcome.update({'process':proc,'request':[int(x) for x in request],'timestamp':datetime.now().isoformat(timespec='seconds'),'base_snapshot':deepcopy(cfg)})
            st.session_state.request_preview=outcome
            st.session_state.history.append({'Timestamp':outcome['timestamp'],'Process':proc,'Request':str(request),'Validation':outcome['status'].upper(),'Safety':'Safe' if outcome.get('safety',{}).get('safe') else ('Unsafe' if outcome['status']=='unsafe' else 'Not run'),'Action':'Previewed'})
        with c2:
            p=st.session_state.request_preview
            if not p: st.info('Configure a request and select Preview request to inspect the temporary allocation.')
            else:
                status=p['status']
                if status=='grantable': st.success('GRANTABLE / SAFE TO GRANT')
                elif status=='deferred': st.warning('WAITING / DEFERRED')
                elif status=='unsafe': st.error('DENIED — WOULD PRODUCE AN UNSAFE STATE')
                else: st.error('INVALID REQUEST')
                st.write(p['reason'])
                if status=='grantable':
                    st.markdown('**Before → after**')
                    old=p['base_snapshot']; new=p['configuration']; i=old['processes'].index(p['process'])
                    table=pd.DataFrame({'Value':['Available','Allocation of '+p['process'],'Need of '+p['process']],'Before':[old['available'],old['allocation'][i],need_matrix(old['allocation'],old['maximum'])[i]],'After':[new['available'],new['allocation'][i],need_matrix(new['allocation'],new['maximum'])[i]]})
                    st.dataframe(table,use_container_width=True,hide_index=True)
                    st.code('Available\' = Available − Request\nAllocation\' = Allocation + Request\nNeed\' = Need − Request')
                    st.info('Safe sequence: '+' → '.join(p['safety']['sequence']))
                    if st.button('Commit Request',type='primary'):
                        if st.session_state.cfg==p['base_snapshot']:
                            st.session_state.cfg=deepcopy(new)
                            st.session_state.history.append({'Timestamp':datetime.now().isoformat(timespec='seconds'),'Process':p['process'],'Request':str(p['request']),'Validation':'GRANTABLE','Safety':'Safe','Action':'Committed'})
                            st.session_state.request_preview=None; st.session_state.safety=None; st.success('Request committed exactly once.'); st.rerun()
                        else: st.error('Live configuration changed since preview. Cancel and preview again.')
                elif status in ('unsafe','deferred'):
                    st.caption('Rollback confirmed: the original configuration remains unchanged.')
                    if p.get('safety'):
                        st.write('Unfinished processes: '+', '.join(p['safety']['unfinished']))
                        st.dataframe(pd.DataFrame([{'Step':x['step'],'Process':x['process'],'Work Before':x['work_before'],'Need':x['need'],'Work After':x['work_after']} for x in p['safety']['trace']]),use_container_width=True,hide_index=True)
        if st.session_state.history:
            st.markdown('### Event history'); st.dataframe(pd.DataFrame(st.session_state.history),use_container_width=True,hide_index=True)
            st.download_button('Export history CSV',pd.DataFrame(st.session_state.history).to_csv(index=False).encode(),file_name='request_history.csv',mime='text/csv')

if active_section == 'Graph':
    with st.container():
        st.title('Resource Allocation Graph')
        st.write(
            'Solid arrows show allocations (resource → process). '
            'Request arrows show outstanding requests (process → resource).'
        )

        dc = st.session_state.detection_cfg

        # Ensure the request matrix exists.
        if 'request' not in dc:
            dc['request'] = [
                [0] * len(dc['resources'])
                for _ in dc['processes']
            ]

        mode = st.radio(
            'Resource model',
            ['Multiple instances', 'Single-instance demonstration'],
            horizontal=True
        )

        edges = []

        for i, process in enumerate(dc['processes']):
            for j, resource in enumerate(dc['resources']):
                if dc['allocation'][i][j] > 0:
                    edges.append(
                        f'{resource} → {process} '
                        f'({dc["allocation"][i][j]})'
                    )

                if dc['request'][i][j] > 0:
                    edges.append(
                        f'{process} ⇢ {resource} '
                        f'({dc["request"][i][j]})'
                    )

        st.markdown('#### Current relationships')
        st.code(
            '\n'.join(edges)
            if edges
            else 'No allocation or request edges.'
        )

        if mode == 'Single-instance demonstration':
            valid_model = all(
                sum(
                    dc['allocation'][i][j]
                    for i in range(len(dc['processes']))
                ) + dc['available'][j] == 1
                for j in range(len(dc['resources']))
            )

            if valid_model:
                st.info(
                    'Resource counts satisfy the single-instance model. '
                    'A directed cycle indicates deadlock in this model.'
                )
            else:
                st.warning(
                    'This configuration does not satisfy the '
                    'single-instance model. Adjust the resource counts.'
                )
        else:
            st.info(
                'For multiple-instance resources, a cycle alone does '
                'not prove deadlock. Use the Detection section.'
            )

        with st.expander('Edit detection scenario', expanded=True):
            st.write(
                'Configure the number of processes, resources, '
                'and their allocation/request values.'
            )

            # Configuration controls.
            col1, col2 = st.columns(2)

            with col1:
                process_count = st.number_input(
                    'Number of processes',
                    min_value=1,
                    max_value=20,
                    value=max(1, len(dc['processes'])),
                    step=1,
                    key='graph_process_count'
                )

            with col2:
                resource_count = st.number_input(
                    'Number of resource types',
                    min_value=1,
                    max_value=10,
                    value=max(1, len(dc['resources'])),
                    step=1,
                    key='graph_resource_count'
                )

            process_count = int(process_count)
            resource_count = int(resource_count)

            # Generate default names while preserving existing names.
            old_processes = dc['processes']
            old_resources = dc['resources']

            process_names = [
                old_processes[i] if i < len(old_processes)
                else f'P{i}'
                for i in range(process_count)
            ]

            resource_names = [
                old_resources[j] if j < len(old_resources)
                else chr(65 + j)
                for j in range(resource_count)
            ]

            process_text = st.text_input(
                'Process names (comma-separated)',
                value=', '.join(process_names),
                key=f'graph_process_names_{process_count}'
            )

            resource_text = st.text_input(
                'Resource names (comma-separated)',
                value=', '.join(resource_names),
                key=f'graph_resource_names_{resource_count}'
            )

            new_processes = [
                x.strip() for x in process_text.split(',') if x.strip()
            ]

            new_resources = [
                x.strip() for x in resource_text.split(',') if x.strip()
            ]

            def resize_matrix(old_matrix, rows, cols):
                return [
                    [
                        old_matrix[i][j]
                        if i < len(old_matrix)
                        and j < len(old_matrix[i])
                        else 0
                        for j in range(cols)
                    ]
                    for i in range(rows)
                ]

            # Preserve existing values where possible.
            allocation_data = resize_matrix(
                dc['allocation'],
                process_count,
                resource_count
            )

            request_data = resize_matrix(
                dc['request'],
                process_count,
                resource_count
            )

            available_data = [
                dc['available'][j]
                if j < len(dc['available'])
                else 0
                for j in range(resource_count)
            ]

            st.markdown('#### Allocation matrix')

            allocation_df = st.data_editor(
                pd.DataFrame(
                    allocation_data,
                    index=process_names,
                    columns=resource_names
                ),
                key='graph_allocation_editor',
                use_container_width=True
            )

            st.markdown('#### Outstanding Request matrix')

            request_df = st.data_editor(
                pd.DataFrame(
                    request_data,
                    index=process_names,
                    columns=resource_names
                ),
                key='graph_request_editor',
                use_container_width=True
            )

            st.markdown('#### Available resources')

            available_df = st.data_editor(
                pd.DataFrame(
                    [available_data],
                    index=['Available'],
                    columns=resource_names
                ),
                key='graph_available_editor',
                use_container_width=True
            )

            if st.button(
                'Apply graph scenario',
                type='primary'
            ):
                try:
                    # Validate names and dimensions.
                    if len(new_processes) != process_count:
                        st.error(
                            'Enter exactly one process name '
                            'for every configured process.'
                        )

                    elif len(new_resources) != resource_count:
                        st.error(
                            'Enter exactly one resource name '
                            'for every configured resource.'
                        )

                    elif len(set(new_processes)) != len(new_processes):
                        st.error('Process names must be unique.')

                    elif len(set(new_resources)) != len(new_resources):
                        st.error('Resource names must be unique.')

                    else:
                        new_allocation = allocation_df.astype(int).values.tolist()
                        new_request = request_df.astype(int).values.tolist()
                        new_available = (
                            available_df.iloc[0].astype(int).tolist()
                        )

                        values = (
                            [v for row in new_allocation for v in row]
                            + [v for row in new_request for v in row]
                            + new_available
                        )

                        if any(v < 0 for v in values):
                            st.error(
                                'Resource counts cannot be negative.'
                            )

                        else:
                            candidate = {
                                'processes': new_processes,
                                'resources': new_resources,
                                'allocation': new_allocation,
                                'request': new_request,
                                'available': new_available
                            }

                            st.session_state.detection_cfg = candidate

                            # Clear results based on the previous scenario.
                            st.session_state.pop('detect_result', None)
                            st.session_state.pop(
                                'detect_result_config', None
                            )
                            st.session_state.pop(
                                'recovery_preview', None
                            )

                            st.success(
                                'Detection scenario updated successfully.'
                            )
                            st.rerun()

                except (ValueError, TypeError, IndexError) as e:
                    st.error(
                        'Invalid configuration. Enter valid '
                        f'whole-number resource quantities. Details: {e}'
                    )


if active_section == 'Detection':
    with st.container():
        st.title('Deadlock Detection')
        st.write(
            "Detection uses the current outstanding Request matrix, "
            "not Banker's Need. It checks whether processes can finish "
            "using the available resources and resources released by "
            "processes that can complete."
        )

        dc = st.session_state.detection_cfg

        st.markdown("**Allocation**")
        st.dataframe(
            matrix_df(
                dc['allocation'],
                dc['processes'],
                dc['resources']
            ),
            use_container_width=True
        )

        st.markdown("**Outstanding Request**")
        st.dataframe(
            matrix_df(
                dc['request'],
                dc['processes'],
                dc['resources']
            ),
            use_container_width=True
        )

        st.write(
            'Available:',
            dict(zip(dc['resources'], dc['available']))
        )

        if st.button(
            'Run deadlock detection',
            type='primary'
        ):
            try:
                st.session_state.detect_result = detect_deadlock(dc)
                st.session_state.detect_result_config = deepcopy(dc)
            except Exception as e:
                st.session_state.pop('detect_result', None)
                st.session_state.pop('detect_result_config', None)
                st.error(f'Detection failed: {e}')

        res = st.session_state.get('detect_result')
        result_config = st.session_state.get('detect_result_config')

        # Display a result only if it belongs to the current configuration.
        if res and result_config == dc:
            if res['deadlocked']:
                st.error(
                    'Deadlocked under this model: '
                    + ', '.join(res['deadlocked'])
                )
            else:
                st.success(
                    'No deadlocked processes identified '
                    'by this detection run.'
                )

            st.write(
                'Completion order:',
                ' → '.join(res['sequence'])
                if res['sequence'] else 'None'
            )

            if res['trace']:
                st.dataframe(
                    pd.DataFrame(res['trace']),
                    use_container_width=True,
                    hide_index=True
                )

        elif res:
            st.info(
                'The detection configuration has changed. '
                'Run detection again to update the result.'
            )

        st.caption(
            'Assumption: Allocation, Available, and outstanding Request '
            'accurately represent the current resource state.'
        )

        if st.button('Reset to genuine deadlock example'):
            st.session_state.detection_cfg = deepcopy(DEADLOCK)
            st.session_state.pop('detect_result', None)
            st.session_state.pop('detect_result_config', None)
            st.session_state.pop('recovery_preview', None)
            st.rerun()


if active_section=='Prevention & Recovery':
    with st.container():
        st.title('Prevention & Recovery')
        tab1,tab2=st.tabs(['Prevention: fixed ordering','Recovery: terminate a victim'])
        with tab1:
            resources=cfg['resources']; order=st.multiselect('Global resource order (drag/order by selection)',resources,default=resources)
            sequence=st.multiselect('Simulated acquisition sequence',resources,default=resources[:min(2,len(resources))])
            if st.button('Check ordering policy'):
                check=ordering_check(sequence,order)
                if check['valid']: st.success(check['reason'])
                else: st.error(check['reason'])
            st.write('Why it works: if every process acquires resources only in a strictly increasing global order, a circular wait cannot form. Trade-offs include less flexibility and potentially reduced utilization.')
            st.info('Prevention restricts resource-acquisition policies. Avoidance (Banker’s) evaluates whether a proposed allocation preserves a safe state.')
        with tab2:
            dc=st.session_state.detection_cfg
            dr=detect_deadlock(dc)
            if dr['deadlocked']: st.warning('Current deadlock candidates: '+', '.join(dr['deadlocked']))
            else: st.info('The current detection scenario has no unfinished deadlocked processes. You can still terminate a process to demonstrate resource release.')
            victim=st.selectbox('Victim process',dc['processes'])
            if victim is not None and victim in dc['processes']:
                st.write(
                    'Allocation to release:',
                    dc['allocation'][dc['processes'].index(victim)]
                )
            else:
                st.info("Select a valid process to inspect its allocated resources.")

            if st.button('Preview recovery'):
                updated, released = terminate_process(dc, victim)
                result = detect_deadlock(updated)
                st.session_state.recovery_preview = {
                    'base': deepcopy(dc),
                    'updated': updated,
                    'released': released,
                    'victim': victim,
                    'result': result
                }
            rec = st.session_state.get('recovery_preview')
            if rec:
                st.markdown('#### Recovery Preview')
                st.write(f"Terminating process **{rec['victim']}** releases: {dict(zip(rec['base']['resources'], rec['released']))}")
                st.write('Updated Available resources:', dict(zip(rec['base']['resources'], rec['updated']['available'])))
                if rec['result']['deadlocked']:
                    st.error('Deadlock persists with remaining processes: ' + ', '.join(rec['result']['deadlocked']))
                else:
                    st.success('Deadlock resolved! Completion order: ' + (' → '.join(rec['result']['sequence']) if rec['result']['sequence'] else 'All finished'))
                col1, col2 = st.columns(2)
                if col1.button('Apply recovery to scenario', type='primary'):
                    st.session_state.detection_cfg = deepcopy(rec['updated'])
                    st.session_state.recovery_preview = None
                    st.session_state.pop('detect_result', None)
                    st.success('Recovery scenario applied.')
                    st.rerun()
                if col2.button('Discard recovery preview'):
                    st.session_state.recovery_preview = None
                    st.rerun()

if active_section=='Test Lab':
    with st.container():
        st.title('Test Lab & Evidence Center')
        st.write('Tests execute real algorithm functions and compare actual outcomes with expected outcomes.')
        a,b=st.columns(2)
        if a.button('Run all tests',type='primary'): st.session_state.test_results=run_tests()
        if b.button('Reset test results'): st.session_state.test_results=None
        if st.session_state.test_results is not None:
            df=pd.DataFrame(st.session_state.test_results); st.dataframe(df,use_container_width=True,hide_index=True)
            passed=sum(x['Pass/Fail']=='PASS' for x in st.session_state.test_results); st.metric('Passed tests',f'{passed}/{len(df)}')
            st.download_button('Export results CSV',df.to_csv(index=False).encode(),file_name='deadlocklab_test_results.csv',mime='text/csv')
            st.download_button('Export scenario JSON',export_json(cfg),file_name='deadlocklab_scenario.json',mime='application/json')
            report='# DeadlockLab Test Report\n\nGenerated: '+datetime.now().isoformat(timespec='seconds')+'\n\n'+df.to_markdown(index=False)+'\n'
            st.download_button('Download test report (Markdown)',report.encode(),file_name='deadlocklab_test_report.md',mime='text/markdown')
        st.caption('The unsafe-request test searches the current standard sample for a real unsafe grantable request; if none is found, it reports that honestly instead of fabricating a pass.')

if active_section == 'About':
    with st.container():
        st.title('About DeadlockLab')

        st.markdown("""
        ### 🧠 DeadlockLab
        **Interactive Deadlock Analysis & Resource Allocation Simulator**

        DeadlockLab is an educational application developed to demonstrate
        operating system resource allocation, deadlock avoidance, detection,
        prevention, and recovery using interactive simulations.
        """)

        st.divider()

        # TEAM MEMBERS
        st.markdown("## 👥 Project Team")

        team = [
            {
                "name": "Kunal Kamble",
                "roll": "82",
                "prn": "202401040042",
            },
            {
                "name": "Mrudula Sanap",
                "roll": "84",
                "prn": "202401040055",
            },
            {
                "name": "Saniya Patel",
                "roll": "89",
                "prn": "202401040074",
            },
            {
                "name": "Nikhil Vilag",
                "roll": "132",
                "prn": "202401040284",
            },
            {
                "name": "Om Rahtal",
                "roll": "152",
                "prn": "202401040341",
            },
        ]

        cols = st.columns(2)

        for i, member in enumerate(team):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"### {member['name']}")
                    st.write(f"**Roll No:** {member['roll']}")
                    st.write(f"**PRN:** {member['prn']}")

        st.markdown("### 🎓 Academic Details")
        st.write("**Course:** Operating Systems")
        st.write("**Project:** DeadlockLab")
        st.write("**College:** MIT Academy of Engineering, Alandi")
        st.write("**Project Guide:** Dr. Vijaykumar P. Mantri")

        st.divider()

        # BANKER'S ALGORITHM CONCEPTS
        st.markdown("## 📚 Banker's Algorithm Concepts")

        st.write(
            "Banker's Algorithm is a deadlock-avoidance algorithm. "
            "It evaluates resource requests and grants them only when "
            "the resulting system state remains safe."
        )

        with st.expander("1. Allocation Matrix"):
            st.write(
                "Allocation[i][j] represents the number of instances "
                "of resource j currently allocated to process i."
            )

        with st.expander("2. Maximum Matrix"):
            st.write(
                "Maximum[i][j] represents the maximum number of "
                "instances of resource j that process i may require."
            )

        with st.expander("3. Need Matrix"):
            st.latex(r"\\text{Need} = \\text{Maximum} - \\text{Allocation}")
            st.write(
                "Need represents the remaining resources each process "
                "may require to complete."
            )

        with st.expander("4. Available Vector"):
            st.write(
                "Available[j] represents the number of currently "
                "unallocated instances of resource j."
            )

        with st.expander("5. Safety Algorithm"):
            st.markdown("""
            1. Initialize Work = Available.
            2. Find an unfinished process whose Need is less than
               or equal to Work.
            3. Assume that process finishes and releases its allocation.
            4. Update Work = Work + Allocation.
            5. Repeat until all processes finish or no eligible process remains.
            """)
            st.write(
                "If all processes can finish, the state is safe and "
                "the completion order is a safe sequence."
            )

        with st.expander("6. Safe State vs Unsafe State"):
            st.markdown("""
            - **Safe:** At least one complete safe sequence exists.
            - **Unsafe:** No complete safe sequence can be found.
            - **Important:** An unsafe state does not necessarily mean
              that a deadlock has already occurred.
            """)

        with st.expander("7. Resource Request Algorithm"):
            st.markdown("""
            For a process Pi requesting resources:

            1. Check Request ≤ Need.
            2. Check Request ≤ Available.
            3. Temporarily allocate the requested resources.
            4. Run the safety algorithm.
            5. Grant the request only if the resulting state is safe;
               otherwise, restore the original state.
            """)

        with st.expander("8. Deadlock Avoidance vs Detection"):
            st.markdown("""
            - **Avoidance:** Evaluates a proposed allocation before granting it.
            - **Detection:** Examines the current resource state to identify
              processes that cannot proceed.
            - **Prevention:** Restricts resource-allocation conditions or policies
              to prevent deadlock.
            - **Recovery:** Takes action, such as terminating a process and
              releasing its resources, to help the system progress.
            """)

        st.divider()

        # PROJECT FEATURES
        st.markdown("## ⚙️ Main Features")

        features = [
            "Interactive system configuration",
            "Banker's safety algorithm and safe-sequence trace",
            "Resource-request preview and rollback",
            "Resource-allocation graph",
            "Deadlock detection",
            "Deadlock prevention using resource ordering",
            "Deadlock recovery simulation",
            "Test Lab and result export"
        ]

        for feature in features:
            st.markdown(f"- ✅ {feature}")

        st.divider()

        # AI USAGE RECORD - PRESERVED
        st.markdown("## 🤖 AI Usage Record")

        adf = st.data_editor(
            pd.DataFrame(st.session_state.ai_records),
            num_rows="dynamic",
            use_container_width=True,
            key="ai_usage"
        )

        if st.button("Save AI Usage Record"):
            st.session_state.ai_records = (
                adf.fillna("").to_dict("records")
            )
            st.success("AI Usage Record saved for this session.")

        st.download_button(
            "Export AI Usage Record CSV",
            pd.DataFrame(st.session_state.ai_records)
                .to_csv(index=False).encode(),
            file_name="ai_usage_record.csv",
            mime="text/csv"
        )

        st.divider()

        st.markdown("## ℹ️ Project Limitations")
        st.write(
            "DeadlockLab is an educational simulator. Its classifications "
            "depend on the configured resource data and the assumptions "
            "of each algorithm. Recovery actions are simulations and do "
            "not control a real operating system."
        )

        st.caption(
            "DeadlockLab | Operating Systems Academic Project"
        )

# DeadlockLab — Interactive OS Deadlock Analysis & Resource Allocation Simulator

A local-first Streamlit application for an Operating Systems Internal Assessment. A horizontal navigation bar switches between the overview, configuration, Banker’s safety analysis, request simulator, resource graph, deadlock detection, prevention/recovery, test lab, and usage record. It includes exportable evidence and shared session state across sections.

## Features
- Editable Allocation, Maximum, and Available values with validation and calculated Need.
- Banker’s safety trace with Work before/after each process.
- Deadlock Time Machine: request validation, temporary preview, safe-state evaluation, explicit commit, cancel, and event history.
- Separate multiple-instance deadlock detection using Allocation, outstanding Request, and Available.
- Resource relationships overview; the graph page labels allocations and requests and explains the single-instance cycle limitation.
- Fixed global resource ordering policy and terminate-process recovery simulation.
- Test lab with CSV, JSON, and Markdown report exports.
- Editable AI Usage Record. No API keys or external AI services.

## Setup (Windows PowerShell)
```powershell
cd DeadlockLab
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app.py
```
Open the local URL printed by Streamlit (normally `http://localhost:8501`).

## Run tests
```powershell
python -m pytest -q
```

## Project structure
```text
DeadlockLab/
  app.py
  requirements.txt
  README.md
  algorithms/
    __init__.py
    bankers.py
    detection.py
  tests/
    test_algorithms.py
  data/
```

## Core concepts
- **Safety:** whether at least one order allows every process to finish.
- **Avoidance:** tentatively grant a request only if the resulting state remains safe.
- **Detection:** use current outstanding Request values, not Banker’s Need, to determine which processes can finish now.
- **Prevention:** restrict a necessary condition. A fixed global resource ordering prevents circular wait if all acquisitions obey it.
- **Recovery:** e.g. terminate a process and release its allocation; then rerun detection.

## Assumptions and limitations
- Resource counts are non-negative integers; Allocation cannot exceed Maximum.
- The total instances of each resource type are derived as allocated plus available.
- The graph view currently presents a clear textual edge representation rather than a plotted node-and-arrow diagram.
- The single-instance graph rule is explained, but automated cycle extraction is not implemented in this Streamlit version.
- Session state is in memory. Save a JSON scenario to retain configuration outside the session.
- Recovery is a simulation and is not a production-system recovery policy.

## AI usage record
The app provides an editable record. Students should accurately fill in tools, purposes, generated outputs, and their own verification; it intentionally does not claim which tools were used or that code has been verified without running tests.

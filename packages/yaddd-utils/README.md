# yaddd-utils

Utilities for [yaddd](https://github.com/netstuff/yaddd): scenario inspection and Mermaid diagram generation.

## Features

- **Scenario inspection** — discover `yaddd` `Scenario` subclasses, their steps, branches and conditions.
- **Mermaid renderers** — turn inspected scenarios into diagrams:
  - flowchart per scenario;
  - grouped flowchart with subgraphs;
  - sequence diagram of step execution;
  - state diagram for `State` subclasses.

## Installation

```bash
pip install yaddd-utils
```

## CLI

Render a Mermaid flowchart from a Python module containing scenarios:

```bash
yaddd-mermaid myapp.scenarios --output diagram.mmd
```

## API

```python
from yaddd_utils.inspect import ScenarioAnalyzer
from yaddd_utils.mermaid import ScenarioRenderer, RenderOptions

analyzer = ScenarioAnalyzer()
model = analyzer.analyze_module("myapp.scenarios")

renderer = ScenarioRenderer(RenderOptions(direction="TD"))
print(renderer.render(model))
```

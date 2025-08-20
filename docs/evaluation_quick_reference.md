# Evaluation System Quick Reference

## 🚀 Quick Start for AI Implementation Agents

### What You're Building
A modular evaluation system for Cooragent that benchmarks the multi-agent system's performance, starting with GAIA benchmark support.

### Key Implementation Files to Create

```
src/evaluation/
├── manager.py          # Start here - orchestrates everything
├── engine.py           # Core execution logic
├── benchmarks/
│   └── gaia/
│       ├── gaia_benchmark.py    # GAIA implementation
│       └── gaia_loader.py       # Dataset handling
```

### Implementation Order (Critical Path)

1. **Day 1-2**: Core Infrastructure
   ```python
   # src/evaluation/manager.py
   class EvaluationManager:
       async def run_evaluation(benchmark_name, config) -> EvaluationResult
   ```

2. **Day 3-4**: GAIA Dataset Loader
   ```python
   # src/evaluation/benchmarks/gaia/gaia_loader.py
   # Use HuggingFace datasets library
   from datasets import load_dataset
   dataset = load_dataset("gaia-benchmark/GAIA")
   ```

3. **Day 5-6**: Workflow Integration
   ```python
   # src/evaluation/workflow_adapter.py
   # Adapt evaluation tasks to existing Cooragent workflow
   async def execute_as_workflow(task) -> Dict
   ```

### Key Integration Points

| Component | Integration File | Method to Modify/Add |
|-----------|-----------------|---------------------|
| CLI | `cli.py` | Add `evaluate` command |
| Workflow | `src/workflow/process.py` | Add evaluation mode |
| Storage | New: `store/evaluation/` | Create directory structure |

### GAIA Benchmark Specifics

**Dataset Structure:**
```json
{
  "task_id": "unique_id",
  "question": "user question",
  "level": 1-3,  // difficulty
  "expected_answer": "answer",
  "file_attachments": [],
  "tools_required": ["search", "python"]
}
```

**Evaluation Criteria:**
- **Accuracy**: Exact match or semantic similarity
- **Tool Usage**: Appropriate tool selection
- **Efficiency**: Steps taken vs optimal

### Code Patterns to Follow

**Use Existing Cooragent Patterns:**
```python
# Follow async/await pattern
async def evaluate_task(task):
    # Use existing workflow
    result = await run_agent_workflow(
        message=task.question,
        mode="production"
    )
    return result

# Use Command pattern for workflow
from cooragent.src.workflow.graph import Command
return Command(goto="next_node", update={"result": result})
```

### Environment Variables to Add

```bash
# .env
EVALUATION_ENABLED=true
HUGGINGFACE_TOKEN=hf_xxxxx  # For GAIA dataset access
EVALUATION_MAX_CONCURRENT=5
```

### Testing Checklist

- [ ] Can load GAIA dataset
- [ ] Can execute single GAIA task
- [ ] Can run full evaluation
- [ ] Results are saved to `store/evaluation/`
- [ ] CLI command works: `python cli.py evaluate --benchmark gaia`

### Common Pitfalls to Avoid

1. **Don't modify core agent logic** - Use adapters
2. **Don't load entire dataset in memory** - Use streaming
3. **Don't block on long tasks** - Use timeouts
4. **Don't forget to handle file attachments** in GAIA tasks

### Dependencies to Install

```bash
pip install datasets  # HuggingFace datasets
pip install pandas   # Data manipulation
pip install plotly   # Visualization (optional)
```

### Quick Test Script

```python
# test_evaluation_basic.py
from src.evaluation.manager import EvaluationManager

async def test_basic():
    manager = EvaluationManager()
    result = await manager.run_evaluation(
        benchmark_name="gaia",
        config={"subset": "validation", "limit": 5}
    )
    print(f"Score: {result.metrics.accuracy}")

# Run: python -m asyncio test_evaluation_basic.py
```

### Debugging Commands

```bash
# Check if evaluation module loads
python -c "from src.evaluation import EvaluationManager; print('✓')"

# Test GAIA dataset access
python -c "from datasets import load_dataset; d = load_dataset('gaia-benchmark/GAIA', split='validation[:5]'); print(f'Loaded {len(d)} tasks')"

# Run single evaluation
python cli.py evaluate --benchmark gaia --limit 1 --debug
```

### File Templates

**Base Benchmark Class:**
```python
# src/evaluation/benchmarks/base.py
from abc import ABC, abstractmethod

class BaseBenchmark(ABC):
    @abstractmethod
    async def load_dataset(self) -> Dataset:
        pass
    
    @abstractmethod
    async def evaluate_response(self, task, response) -> Score:
        pass
```

**GAIA Implementation:**
```python
# src/evaluation/benchmarks/gaia/gaia_benchmark.py
class GAIABenchmark(BaseBenchmark):
    async def load_dataset(self):
        from datasets import load_dataset
        hf_dataset = load_dataset("gaia-benchmark/GAIA")
        return self._convert_to_internal_format(hf_dataset)
```

### Success Metrics

✅ **Minimum Viable Implementation:**
- Load 10 GAIA tasks
- Execute through Cooragent
- Calculate accuracy score
- Save results to file

✅ **Full Implementation:**
- All GAIA tasks supported
- Parallel execution
- Comprehensive metrics
- HTML report generation

### Direct Python API (Alternative to CLI)

If your environment has heavy CLI dependencies, you can run evaluations via a lightweight script:

```bash
# Using conda env py310
eval_cmd="conda run -n py310 python cooragent/scripts/run_evaluation.py -b gaia -l 0"
$eval_cmd
# Output example:
# Run ID: GAIABenchmark-<timestamp>
# Benchmark: GAIA
# Tasks: 0
# Aggregate Score: 0.000
```

This avoids importing the full CLI stack and is recommended for CI or minimal environments.

### Need Help?

1. **Reference**: `cooragent/PROJECT.md` for system architecture
2. **Pattern**: Check `src/workflow/process.py` for workflow patterns
3. **Tools**: See `src/tools/` for tool integration examples
4. **LLM**: Check `src/llm/agents.py` for agent configuration

---

**Remember**: Start simple, test often, integrate incrementally! 
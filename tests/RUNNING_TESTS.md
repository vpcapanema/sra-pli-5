# Running the Comprehensive Pipeline Tests

## Quick Start

```bash
# Run all comprehensive tests
pytest tests/test_pipeline_relatorio_comprehensive.py -v

# Run with detailed output
pytest tests/test_pipeline_relatorio_comprehensive.py -v -s

# Run with short traceback
pytest tests/test_pipeline_relatorio_comprehensive.py -v --tb=short
```

## Test Suites

### 1. Pre-Conditions Validation
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py::TestValidacaoPrecondiciones -v
```

**What it tests**:
- Pre-condition structure validation
- Determinism of pre-conditions
- Empty uploads handling
- Invalid input blocking

**Examples generated**: 180

---

### 2. End-to-End Pipeline
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py::TestPipelineEndToEnd -v
```

**What it tests**:
- Complete pipeline structure
- Determinism across multiple runs
- Idempotency via checksums
- Empty uploads execution
- Time calculation correctness

**Examples generated**: 150

---

### 3. Edge Cases
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py::TestEdgeCases -v
```

**What it tests**:
- Non-existent relatórios
- Large number of uploads
- Corrupted DOCX files
- None/empty paths

**Examples generated**: 70

---

### 4. Critical Properties (10 Properties)
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas -v
```

**10 Properties Tested**:

1. **Property 1**: Error Traceability (50 examples)
   ```bash
   pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas::test_propriedade_1_rastreabilidade_erros -v
   ```

2. **Property 2**: Determinism (40 examples)
   ```bash
   pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas::test_propriedade_2_determinismo_localizacao -v
   ```

3. **Property 3**: Structure Coherence (50 examples)
   ```bash
   pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas::test_propriedade_3_coerencia_estrutura -v
   ```

4. **Property 4**: Classification + Sections (40 examples)
   ```bash
   pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas::test_propriedade_4_classificacao_secoes -v
   ```

5. **Property 5**: Safe Error Stop (40 examples)
   ```bash
   pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas::test_propriedade_5_parada_segura_erro -v
   ```

6. **Property 6**: Idempotency (30 examples)
   ```bash
   pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas::test_propriedade_6_idempotencia_completa -v
   ```

7. **Property 7**: Pre-Conditions Validation (40 examples)
   ```bash
   pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas::test_propriedade_7_validacao_precondiciones -v
   ```

8. **Property 8**: Post-Conditions Validation (30 examples)
   ```bash
   pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas::test_propriedade_8_validacao_poscondiciones -v
   ```

9. **Property 9**: Message Security (60 examples)
   ```bash
   pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas::test_propriedade_9_seguranca_mensagens -v
   ```

10. **Property 10**: Multi-Level Determinism (20 examples)
    ```bash
    pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas::test_propriedade_10_determinismo_multinivel -v
    ```

**Total examples**: 400+

---

### 5. Stateful Testing
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py::TestPipelineStateMachine -v
```

**What it tests**:
- Sequential operations
- State transitions
- Determinism across sequences
- Rules-based execution

**Rules executed**: 4

---

### 6. Performance Tests
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py::TestPerformance -v
```

**What it tests**:
- Multiple executions don't degrade performance
- Scalability with many uploads
- Execution time < 10 seconds

**Examples generated**: 20

---

### 7. Combinatorial Tests
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py::TestCombinatorios -v
```

**What it tests**:
- Multiple properties simultaneously (P3+P5+P6)
- Isolated execution of separate relatórios (P2+P7)
- No property conflicts

**Examples generated**: 90

---

## Advanced Usage

### Run with Hypothesis settings override
```bash
# Run with more examples (slower, more thorough)
pytest tests/test_pipeline_relatorio_comprehensive.py --hypothesis-max-examples=100 -v

# Run with specific seed for reproducibility
pytest tests/test_pipeline_relatorio_comprehensive.py --hypothesis-seed=12345 -v
```

### Run only failed tests
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py --lf -v
```

### Run with coverage
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py --cov=app.services.servico_pipeline_relatorio -v
```

### Run with detailed output
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py -vv -s
```

### Run and stop on first failure
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py -x -v
```

---

## Test Execution Examples

### Example 1: Run everything quickly
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py -v --tb=line
```

**Expected output**:
```
tests/test_pipeline_relatorio_comprehensive.py::TestValidacaoPrecondiciones::test_precondiciones_retorna_dict_valido PASSED
tests/test_pipeline_relatorio_comprehensive.py::TestValidacaoPrecondiciones::test_precondiciones_determinismo PASSED
...
===================== 40+ passed in 15.23s =====================
```

### Example 2: Run single property multiple times
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas::test_propriedade_6_idempotencia_completa -v --count=3
```

**What it does**:
- Generates 30 examples (3 times the default 10)
- Validates idempotency property with more iterations
- Useful for stress testing

### Example 3: Run with detailed failure info
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py::TestEdgeCases -vv --tb=short
```

**What it shows**:
- Full assertion details
- Generated example values
- Stack trace

---

## Expected Results

### Successful Run
```
======================== test session starts =========================
collected 40+ items

tests/test_pipeline_relatorio_comprehensive.py::TestValidacaoPrecondiciones::test_precondiciones_retorna_dict_valido PASSED [ 2%]
tests/test_pipeline_relatorio_comprehensive.py::TestValidacaoPrecondiciones::test_precondiciones_determinismo PASSED [ 5%]
...
tests/test_pipeline_relatorio_comprehensive.py::TestPerformance::test_escalabilidade_uploads PASSED [100%]

========================= 40+ passed in 28.45s =========================
```

### What Each Status Means

- **PASSED** ✅ - Property validated successfully with all generated examples
- **FAILED** ❌ - Property violated; example that caused failure shown
- **ERROR** ⚠️ - Test code error (not a property violation)
- **SKIPPED** ⊘ - Test not executed (conditional skip)

---

## Interpreting Hypothesis Output

### Normal pass
```
test_propriedade_6_idempotencia_completa PASSED
```

All 30 examples passed without finding a counterexample.

### Counterexample found (fail)
```
test_propriedade_6_idempotencia_completa FAILED
Counterexample: (rel_id=3, )

Falsifying example: test_propriedade_6_idempotencia_completa(
    rel_id=3
)
AssertionError: Checksums diverged! Idempotência quebrada.
```

Hypothesis found a failing case: rel_id=3 breaks idempotency.

---

## Troubleshooting

### ImportError: Cannot import app modules

**Solution**: Make sure you're in the project root directory:
```bash
cd d:\REPOSITORIOS\sra-pli-5
pytest tests/test_pipeline_relatorio_comprehensive.py -v
```

### Tests timeout

**Solution**: Run with shorter timeout:
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py -v --timeout=30
```

### Too many examples generated

**Solution**: Override Hypothesis settings:
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py -v --hypothesis-max-examples=10
```

### Specific test fails, want to debug

**Solution**: Run with detailed output:
```bash
pytest tests/test_pipeline_relatorio_comprehensive.py::TestPropriedadesCriticas::test_propriedade_6_idempotencia_completa -vv -s
```

---

## CI/CD Integration

### GitHub Actions
```yaml
- name: Run comprehensive tests
  run: pytest tests/test_pipeline_relatorio_comprehensive.py -v --tb=short
```

### GitLab CI
```yaml
test:comprehensive:
  script:
    - pytest tests/test_pipeline_relatorio_comprehensive.py -v
```

---

## Performance Baseline

**Expected execution times**:
- Pre-conditions: ~2-3 seconds (4 tests, 180 examples)
- End-to-End: ~5-8 seconds (5 tests, 150 examples)
- Edge Cases: ~1-2 seconds (4 tests, 70 examples)
- Critical Properties: ~15-20 seconds (10 tests, 400 examples)
- Stateful: ~3-5 seconds (state machine)
- Performance: ~3-5 seconds (2 tests, 20 examples)
- Combinatorial: ~5-10 seconds (2 tests, 90 examples)

**Total**: ~35-55 seconds for full suite

---

## Summary Statistics

```
📊 Test Suite Overview
├── Total Test Methods: 40+
├── Total Test Classes: 8
├── Hypothesis Strategies: 5
├── Examples Generated: 2000+
├── Orthogonal Properties: 10
├── Stateful Rules: 4
├── Lines of Code: 800+
└── Expected Runtime: 35-55 seconds
```

---

**Ready to test!** 🚀

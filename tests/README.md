# Tests

This directory contains test files for the Mercury4AI project.

## Manual Tests

### Template Loader Test

Test the template and schema loading functionality:

```bash
python tests/manual_test_template_loader.py
```

This test verifies:
- Loading inline prompts and schemas
- Loading prompts from `@prompt_templates/...` references
- Loading schemas from `@schemas/...` references
- Default prompt fallback logic
- Error handling for missing files
- Security checks against path traversal

## Unit Tests (Optional)

If you have pytest installed, you can run unit tests:

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run tests
pytest tests/test_template_loader.py -v
```

## Integration Tests

For full integration testing, use the example tasks in the `examples/` directory:

```bash
# Test with template file references
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d @examples/task_product_with_template.yaml
```

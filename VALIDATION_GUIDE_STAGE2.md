# Manual Validation Guide for Stage 2 (LLM Extraction) Fixes

This guide provides step-by-step instructions for manual validation of the Stage 2 fixes.

## Expected Behaviors After Fix

### 1. Stage 2 Enabled with Valid Config

- Logs should show:
  - `"Stage 2 (LLM extraction) START"` with all parameters
  - `"Stage 2 (LLM extraction) END - SUCCESS"` with output size
  - `"✓ Saved structured data (Stage 2) to MinIO: .../json/{doc_id}.json"`
- MinIO should contain: `{run_id}/json/{document_id}.json`
- resource_index.json should have: `"json_path": ".../json/{doc_id}.json"` (NOT null)
- Summary should show: `"Stage 2 (LLM extraction): N documents"`

### 2. Stage 2 Missing Prompt Template

- Logs should show: `"Stage 2 extraction disabled: LLM config present but no prompt_template provided"`
- error_log.json should contain entry with `stage: "stage2"`
- `/api/runs/{run_id}/logs` should return error_log_url
- Summary should show: `"Stage 2: DISABLED"` or `"Stage 2: FAILED"`

### 3. Stage 2 Missing API Key

- Logs should show:
  - `"No API key provided for LLM extraction"`
  - `"Stage 2 extraction disabled: Failed to create LLMConfig"`
- Summary should show: `"Stage 2: DISABLED"` or `"Stage 2: FAILED"`

### 4. Stage 2 LLM Call Failed

- Logs should show:
  - `"Stage 2 (LLM extraction) START"` with all parameters
  - `"Stage 2 (LLM extraction) END - FAILED"` with error message
- error_log.json should contain entry with `stage: "stage2"` and error details
- `/api/runs/{run_id}/logs` should return error_log_url
- resource_index.json should have: `"json_path": null`
- Summary should show: `"Stage 2: FAILED (N errors)"`

## Validation Steps

### Step 1: Start the application

```bash
docker-compose up -d
```

### Step 2: Create a test task with valid LLM config

```bash
curl -X POST "http://localhost:8000/api/tasks" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Stage 2 Valid Test",
    "urls": ["https://example.com"],
    "llm_provider": "openai",
    "llm_model": "gpt-4",
    "llm_params": {
      "api_key": "your-real-api-key",
      "temperature": 0.1
    },
    "prompt_template": "Extract the title and main content from this page.",
    "output_schema": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "content": {"type": "string"}
      }
    }
  }'
```

Save the returned `task_id`.

### Step 3: Run the task

```bash
curl -X POST "http://localhost:8000/api/tasks/{task_id}/run" \
  -H "X-API-Key: your-api-key"
```

Save the returned `run_id`.

### Step 4: Check worker logs for Stage 2 START/END

```bash
docker-compose logs -f worker | grep -A 10 "Stage 2"
```

Expected output:
- "Stage 2 (LLM extraction) START"
- Shows: URL, Provider, Model, API key: present, Prompt length, Schema configured
- "Stage 2 (LLM extraction) END - SUCCESS"
- Shows: Output size, JSON keys

### Step 5: Check MinIO for JSON file

1. Open MinIO console: http://localhost:9001
2. Navigate to mercury4ai bucket
3. Find: `{date}/{run_id}/json/{document_id}.json`
4. Download and verify the JSON content

### Step 6: Check resource_index.json

```bash
curl "http://localhost:8000/api/runs/{run_id}/logs" \
  -H "X-API-Key: your-api-key"
```

Download the manifest_url, then check resource_index.json:
- Should have document with `"json_path": ".../{document_id}.json"` (NOT null)

### Step 7: Check run summary in logs

```bash
docker-compose logs worker | grep "Data cleaning performed"
```

Expected: `"Stage 2 (LLM extraction): 1 documents"` (or appropriate count)

### Step 8: Test with missing prompt (error case)

```bash
curl -X POST "http://localhost:8000/api/tasks" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Stage 2 Missing Prompt Test",
    "urls": ["https://example.com"],
    "llm_provider": "openai",
    "llm_model": "gpt-4",
    "llm_params": {
      "api_key": "your-real-api-key"
    }
  }'
```

Run and check:
- Logs show "Stage 2 extraction disabled"
- Summary shows "Stage 2: DISABLED"

### Step 9: Test with missing API key (error case)

```bash
curl -X POST "http://localhost:8000/api/tasks" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Stage 2 No API Key Test",
    "urls": ["https://example.com"],
    "llm_provider": "openai",
    "llm_model": "gpt-4",
    "prompt_template": "Extract the title and content."
  }'
```

Run and check:
- Logs show "No API key provided for LLM extraction"
- Summary shows "Stage 2: DISABLED" or "Stage 2: FAILED"

### Step 10: Verify error_log.json when errors occur

For any failed run with Stage 2 errors:

```bash
curl "http://localhost:8000/api/runs/{run_id}/logs" \
  -H "X-API-Key: your-api-key"
```

Response should include:
- `"error_log_url": "https://..."`
- `"error_log_path": ".../logs/error_log.json"`

Download error_log.json and verify:
- Contains entries with `"stage": "stage2"`
- Has clear error messages
- Includes URL and timestamp

## Validation Checklist

- [ ] Stage 2 START log shows all parameters (URL, provider, model, API key presence, etc.)
- [ ] Stage 2 END log shows result (success/failure, output size, JSON keys)
- [ ] JSON file created in MinIO at `.../json/{document_id}.json` when Stage 2 succeeds
- [ ] resource_index.json has non-null json_path when Stage 2 succeeds
- [ ] JSON save log shows document ID, size, and source URL
- [ ] Stage 2 errors captured in error_log.json with `"stage": "stage2"`
- [ ] `/api/runs/{run_id}/logs` returns error_log_url when errors exist
- [ ] Summary accurately reflects Stage 2 status (succeeded/failed/disabled)
- [ ] Summary shows "Stage 2: FAILED" when enabled but failed
- [ ] Summary shows "Stage 2 (LLM extraction): N documents" only when succeeded

## Troubleshooting

### If json_path is still null

- Check Stage 2 START/END logs to see if Stage 2 actually ran
- Check for Stage 2 errors in error_log.json
- Verify LLM API key is valid and has credits
- Check prompt_template is not empty

### If error_log_url not returned

- Check if error_log.json actually exists in MinIO
- Verify run.logs_path is set
- Check MinIO connectivity

### If summary shows wrong Stage 2 status

- Check stage2_success_count in worker logs
- Verify stage2_status is properly tracked for each URL
- Check if Stage 2 errors are being captured

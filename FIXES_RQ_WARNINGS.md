# Fix for RQ Duplicate Parameter Warnings

## Issue Description

When running the RQ worker with version 2.0.0 and Click >= 8.2.0, you may see warnings like:

```
UserWarning: The parameter --serializer is used more than once. Remove its duplicate as parameters should be unique.
UserWarning: The parameter -S is used more than once. Remove its duplicate as parameters should be unique.
```

These warnings appear when starting the worker:
```bash
rq worker --url redis://redis:6379/0 crawl_tasks
```

## Root Cause

This is a known issue in RQ tracked at [rq/rq#2253](https://github.com/rq/rq/issues/2253). The RQ CLI code has duplicate parameter definitions for `--serializer` and `-S` that Click 8.2.0+ detects and warns about.

## Solution

The fix involves two changes to `requirements.txt`:

1. **Upgrade RQ to 2.6.1**: This gets the latest bug fixes and improvements
2. **Pin Click to < 8.2.0**: This prevents the duplicate parameter warnings

```diff
 # Task Queue
-rq==2.0.0
+rq==2.6.1
 redis==5.2.0
+click<8.2.0  # Pin click version to avoid duplicate parameter warnings with RQ (see rq/rq#2253)
```

## Benefits

- ✅ Eliminates all duplicate parameter warnings
- ✅ Gets latest RQ features (cron scheduler, better Windows support, etc.)
- ✅ Maintains backward compatibility with existing code
- ✅ No functional impact on crawling or worker operations

## Verification

After applying the fix, you can verify that the warnings are gone by:

1. Rebuilding the Docker container:
   ```bash
   docker-compose build worker
   ```

2. Starting the worker:
   ```bash
   docker-compose up worker
   ```

3. Checking the logs - you should no longer see the UserWarning messages:
   ```bash
   docker-compose logs worker
   ```

Alternatively, run the verification script:
```bash
python verify_dependencies.py
```

## Alternative Solutions

If you cannot pin Click version (e.g., due to other dependencies), you can:

1. **Wait for upstream fix**: Monitor [rq/rq#2253](https://github.com/rq/rq/issues/2253) for an official fix
2. **Suppress warnings programmatically**: Add this to your worker startup code:
   ```python
   import warnings
   warnings.filterwarnings("ignore", message="The parameter .* is used more than once")
   ```

## References

- RQ Issue: https://github.com/rq/rq/issues/2253
- RQ Releases: https://github.com/rq/rq/releases
- Click Changelog: https://click.palletsprojects.com/en/8.1.x/changes/

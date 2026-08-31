## Summary

<!-- What does this PR change and why? -->

## Type

- [ ] Bug fix
- [ ] Feature
- [ ] Documentation
- [ ] CI / tooling
- [ ] Refactor

## Test plan

- [ ] `python -m pytest tests/unit tests/integration -m "not live" -q`
- [ ] `python scripts/validate_workflow.py Workflows`
- [ ] `.\scripts\preflight.ps1 -SkipLM` (if touching stack/scripts)
- [ ] Manual UI check at http://localhost:8080 (if UI change)

## Checklist

- [ ] English docs updated; Persian `.fa.md` companions updated when user-facing
- [ ] No secrets committed (`.env`, tokens, credentials)
- [ ] `config/models.yaml` remains SSOT for model IDs when models change

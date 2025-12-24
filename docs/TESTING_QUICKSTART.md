# Testing Quick Start Guide

## ✅ Setup Complete

Your testing infrastructure is now fully configured and working!

## Quick Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run specific test category
pytest -m auth          # Authentication tests
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Current Status

- ✅ **81 Tests Created**
- ✅ **35% Code Coverage** (baseline established)
- ✅ **All Fixtures Working**
- ✅ **Mocking Configured** (Supabase, AI, Database)

## Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| Auth | 8 | Authentication & authorization |
| Profiles | 14 | User profile management |
| CVs | 19 | CV upload, parsing, management |
| AI Router | 20 | AI provider routing & costs |
| Jobs | 20 | Job scraping & search |

## Example Test Run

```bash
(venv) $ pytest tests/test_auth.py -v

tests/test_auth.py::TestHealthCheck::test_health_check_success PASSED
tests/test_auth.py::TestHealthCheck::test_health_check_no_auth_required PASSED
tests/test_auth.py::TestAuthentication::test_protected_route_without_token PASSED
tests/test_auth.py::TestAuthentication::test_protected_route_with_invalid_token PASSED
tests/test_auth.py::TestAuthentication::test_protected_route_with_mock_auth PASSED
tests/test_auth.py::TestAuthorizationHeaders::test_bearer_token_format PASSED
tests/test_auth.py::TestAuthorizationHeaders::test_missing_authorization_header PASSED
tests/test_auth.py::TestAuthorizationHeaders::test_empty_authorization_header PASSED

======================== 8 passed in 1.05s ========================
```

## Key Files

- `pytest.ini` - pytest configuration
- `tests/conftest.py` - Test fixtures and mocks
- `tests/test_*.py` - Test suites
- `tests/README.md` - Comprehensive testing guide
- `TESTING_SETUP_SUMMARY.md` - Complete documentation

## Dependencies Installed

```
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
httpx<0.28
```

## Next Steps

1. **Increase Coverage**: Target 80%+ coverage
2. **Add Integration Tests**: Test with real database
3. **CI/CD Integration**: Add GitHub Actions
4. **Error Handling Tests**: Test failure scenarios
5. **Performance Tests**: Add load testing

## Common Issues

### Issue: Module not found 'app'
**Solution**: Make sure you're in the `backend/` directory and have `pythonpath = .` in `pytest.ini`

### Issue: Coverage arguments not recognized
**Solution**: Install pytest-cov: `pip install pytest-cov`

### Issue: httpx version conflict
**Solution**: Use `httpx<0.28` for compatibility with FastAPI 0.104.1

## Production Checklist

Before deploying to production:

- [ ] Test coverage ≥ 80%
- [ ] All critical paths tested
- [ ] Integration tests passing
- [ ] CI/CD pipeline configured
- [ ] Load tests completed
- [ ] Security tests added
- [ ] Error handling validated
- [ ] Database transactions tested

## Support

For detailed information, see:
- [tests/README.md](tests/README.md) - Full testing guide
- [TESTING_SETUP_SUMMARY.md](../TESTING_SETUP_SUMMARY.md) - Complete setup docs

---

**Testing infrastructure ready for production development!** 🚀

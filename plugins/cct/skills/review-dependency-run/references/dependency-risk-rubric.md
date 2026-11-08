# Dependency Risk Rubric

## Risk Levels

### Low
- Patch updates only
- No breaking changes identified
- All tests pass
- No deprecated API usage found in project

### Medium
- Minor updates with some deprecations
- Tests pass after applying fixes
- Breaking changes identified but limited to configuration or non-critical paths
- Transitive major bumps with no direct usage

### High
- Major updates with breaking changes requiring code modifications
- Tests failing due to dependency changes (even after attempted fixes)
- Security-related changes that alter authentication or authorization behavior
- Multiple direct dependencies updated simultaneously with interdependencies

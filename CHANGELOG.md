# Changelog

All notable changes to Zynexra will be documented in this file.

---

## [v0.2.0] - 2026-07-06

### Added
- Cross-clause structural inconsistency detection
- Pipeline-generated Structural Inconsistency issues
- Improved contradiction scanning across clauses
- Additional regression tests for contradiction detection
- Investigation documentation for benchmark regressions

### Changed
- Refined CROSS-CLAUSE CONTRADICTION SCAN prompt
- Improved contradiction classification logic
- Improved clause splitting for DOCX and text extraction
- Improved audit prompt guidance for legal reasoning

### Fixed
- Restored benchmark score to the original baseline
- Fixed NDA-02 prompt regression
- Fixed false confidentiality survival suppression
- Improved quoted-text extraction for generated structural inconsistency findings

### Benchmark

Composite: **88.00**

- TP: 10
- FP: 6
- FN: 0

---

## [v0.1.0] - 2026-05-30

Initial public release.
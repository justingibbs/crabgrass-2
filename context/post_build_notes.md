# Post-Build Notes

Technical observations and future considerations captured during implementation.

---

## Dual Storage: DuckDB + JJ

**Current State (Slice 4):**

Kernel file content is stored in two places:

| Storage | Role | Location |
|---------|------|----------|
| DuckDB | Source of truth for reads/writes | `kernel_files` table |
| JJ | Version history tracking | `data/ideas/{idea_id}/kernel/*.md` |

**Data Flow:**
```
Save → DuckDB (via kernel_file_concept.update())
     → Filesystem + JJ commit (via version_concept.commit())

Read → DuckDB only
History → JJ only
```

**Consideration:**

This dual storage is redundant. Two potential approaches:

1. **Keep DuckDB as source of truth** (current)
   - Pros: Database queries, relations, future full-text search
   - Cons: Content duplicated, sync risk if they diverge

2. **Make JJ/filesystem the source of truth**
   - Pros: Single source, simpler architecture, JJ handles all versioning
   - Cons: Need to read files from disk, no SQL queries on content

**Recommendation:** Evaluate in a future slice whether to consolidate. For now, the dual approach works and DuckDB provides flexibility for future features (embeddings, search).

---

## CDN vs Vendored Dependencies

**Current State (Slice 4):**

marked.js is loaded via CDN in `frontend/index.html`:
```html
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
```

**Consideration:**

Move to vendored dependencies for:
- Offline development capability
- Version pinning / reproducibility
- No external network dependency at runtime
- Security (avoid CDN compromise risk)

**Options:**
1. Download and commit to `frontend/js/vendor/marked.min.js`
2. Use a simple bundler (esbuild) to manage dependencies
3. Keep CDN for now, vendor when adding more dependencies

**Recommendation:** When adding a second external dependency, evaluate vendoring all JS libs to `frontend/js/vendor/` with version numbers in filenames.

---

## Future Items

- [ ] Decide on storage consolidation (DuckDB vs JJ as single source)
- [ ] Evaluate vendoring strategy when adding next JS dependency
- [ ] Consider adding integrity hashes to CDN script tags as interim measure

---

*Created: 2026-01-02*

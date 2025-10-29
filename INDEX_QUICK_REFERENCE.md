# Database Indexes Quick Reference

## All Indexes by Table

### Users Table
| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `users_pkey` | UNIQUE | id | Primary key |
| `ix_users_email` | UNIQUE | email | Unique email lookup |
| `idx_users_is_active` | INDEX | is_active | Filter active users |

**Common Queries**:
```sql
-- Login by email
SELECT * FROM users WHERE email = 'user@example.com';

-- Get active users
SELECT * FROM users WHERE is_active = true;
```

---

### Jobs Table
| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `jobs_pkey` | UNIQUE | id | Primary key |
| `ix_jobs_user_id` | INDEX | user_id | Foreign key to users |
| `ix_jobs_status` | INDEX | status | Filter by job status |
| `idx_jobs_user_status` | INDEX | user_id, status | Composite filter |
| `idx_jobs_created_at` | INDEX | created_at DESC | Sort by recency |

**Common Queries**:
```sql
-- User's pending jobs
SELECT * FROM jobs WHERE user_id = 1 AND status = 'pending';

-- Recent jobs
SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10;

-- User's recent jobs
SELECT * FROM jobs WHERE user_id = 1 ORDER BY created_at DESC;
```

---

### OCR Results Table
| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `ocr_results_pkey` | UNIQUE | id | Primary key |
| `uq_job_page` | UNIQUE | job_id, page_num | Prevent duplicate pages |
| `ix_ocr_results_job_id` | INDEX | job_id | Foreign key to jobs |
| `idx_ocr_book_title` | INDEX | book_title | Filter by book |
| `idx_ocr_job_page` | INDEX | job_id, page_num | Composite lookup |
| `idx_ocr_created_at` | INDEX | created_at DESC | Sort by recency |

**Common Queries**:
```sql
-- Get all pages for a job
SELECT * FROM ocr_results WHERE job_id = 'abc-123' ORDER BY page_num;

-- Find specific page
SELECT * FROM ocr_results WHERE job_id = 'abc-123' AND page_num = 5;

-- Recent OCR results
SELECT * FROM ocr_results ORDER BY created_at DESC LIMIT 10;

-- OCR results for a book
SELECT * FROM ocr_results WHERE book_title = 'My Book';
```

---

### Summaries Table
| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `summaries_pkey` | UNIQUE | id | Primary key |
| `ix_summaries_job_id` | INDEX | job_id | Foreign key to jobs |
| `idx_summary_job` | INDEX | job_id | Job lookup (duplicate) |
| `idx_summary_book_title` | INDEX | book_title | Filter by book |
| `idx_summaries_created_at` | INDEX | created_at DESC | Sort by recency |
| `idx_summaries_format` | INDEX | format | Filter by format |
| `idx_summaries_granularity` | INDEX | granularity | Filter by detail level |

**Common Queries**:
```sql
-- Get summaries for a job
SELECT * FROM summaries WHERE job_id = 'abc-123';

-- Recent markdown summaries
SELECT * FROM summaries
WHERE format = 'markdown'
ORDER BY created_at DESC;

-- Detailed summaries
SELECT * FROM summaries WHERE granularity = 'detailed';

-- Recent summaries for a book
SELECT * FROM summaries
WHERE book_title = 'My Book'
ORDER BY created_at DESC;
```

---

### Knowledge Table
| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `knowledge_pkey` | UNIQUE | id | Primary key |
| `idx_knowledge_book_title` | INDEX | book_title | Filter by book |
| `idx_knowledge_format` | INDEX | format | Filter by format |
| `idx_knowledge_score` | INDEX | score | Sort by quality |
| `idx_knowledge_created_at` | INDEX | created_at DESC | Sort by recency |

**Common Queries**:
```sql
-- Recent knowledge entries
SELECT * FROM knowledge ORDER BY created_at DESC LIMIT 10;

-- Knowledge for a specific book
SELECT * FROM knowledge WHERE book_title = 'My Book';

-- High-quality knowledge entries
SELECT * FROM knowledge WHERE score > 0.8 ORDER BY score DESC;
```

---

### Feedbacks Table
| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `feedbacks_pkey` | UNIQUE | id | Primary key |
| `ix_feedbacks_user_id` | INDEX | user_id | Foreign key to users |
| `idx_feedback_user` | INDEX | user_id | User lookup (duplicate) |
| `idx_feedback_rating` | INDEX | rating | Filter by rating |
| `idx_feedback_created` | INDEX | created_at | Sort by recency |

**Common Queries**:
```sql
-- Recent feedback
SELECT * FROM feedbacks ORDER BY created_at DESC LIMIT 10;

-- User's feedback
SELECT * FROM feedbacks WHERE user_id = 1 ORDER BY created_at DESC;

-- High-rated feedback
SELECT * FROM feedbacks WHERE rating >= 4 ORDER BY created_at DESC;

-- Poor ratings (for improvement)
SELECT * FROM feedbacks WHERE rating <= 2 ORDER BY created_at DESC;
```

---

### Biz Files Table
| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `biz_files_pkey` | UNIQUE | id | Primary key |
| `idx_biz_file_filename` | INDEX | filename | Search by filename |
| `idx_biz_file_uploaded` | INDEX | uploaded_at | Sort by upload time |

**Common Queries**:
```sql
-- Recent uploads
SELECT * FROM biz_files ORDER BY uploaded_at DESC LIMIT 10;

-- Find file by name
SELECT * FROM biz_files WHERE filename = 'document.pdf';
```

---

### Biz Cards Table (RAG)
| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `biz_cards_pkey` | UNIQUE | id | Primary key |
| `ix_biz_cards_file_id` | INDEX | file_id | Foreign key to biz_files |
| `idx_biz_card_file` | INDEX | file_id | File lookup (duplicate) |
| `idx_biz_card_score` | INDEX | score | Quality filtering |
| `idx_biz_card_indexed` | INDEX | indexed_at | Sort by index time |

**Common Queries**:
```sql
-- Cards for a file
SELECT * FROM biz_cards WHERE file_id = 123;

-- Recent indexed cards
SELECT * FROM biz_cards ORDER BY indexed_at DESC LIMIT 10;

-- High-quality cards
SELECT * FROM biz_cards WHERE score > 0.8;
```

---

## Index Maintenance Commands

### Check Index Usage Statistics
```sql
SELECT
    schemaname,
    relname as table_name,
    indexrelname as index_name,
    idx_scan as times_used,
    idx_tup_read as tuples_read
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### Find Unused Indexes
```sql
SELECT
    schemaname,
    relname as table_name,
    indexrelname as index_name,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
  AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Check Index Sizes
```sql
SELECT
    schemaname,
    relname as table_name,
    indexrelname as index_name,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Rebuild Bloated Indexes
```sql
-- If an index becomes fragmented, rebuild it
REINDEX INDEX idx_jobs_created_at;

-- Or rebuild all indexes for a table
REINDEX TABLE jobs;
```

---

## Performance Tips

### When to Use Which Index

1. **Equality lookups**: Use single-column indexes
   ```sql
   WHERE status = 'pending'  -- uses idx_jobs_status
   ```

2. **Range queries**: Use B-tree indexes (default)
   ```sql
   WHERE created_at > '2024-01-01'  -- uses idx_jobs_created_at
   ```

3. **Sorting**: Use DESC indexes for DESC queries
   ```sql
   ORDER BY created_at DESC  -- uses idx_jobs_created_at (DESC)
   ```

4. **Composite filters**: Use multi-column indexes
   ```sql
   WHERE user_id = 1 AND status = 'pending'  -- uses idx_jobs_user_status
   ```

### Index Caveats

**Indexes will NOT be used for**:
- Functions on columns: `WHERE LOWER(status) = 'pending'`
- Type mismatches: `WHERE user_id = '1'` (if user_id is INT)
- Leading wildcards: `WHERE title LIKE '%book%'`
- NULL checks: `WHERE user_id IS NULL` (unless partial index)

**Indexes WILL be used for**:
- Exact matches: `WHERE status = 'pending'`
- Range queries: `WHERE created_at > '2024-01-01'`
- Prefix searches: `WHERE title LIKE 'book%'`
- Sorting: `ORDER BY created_at DESC`
- Joins: `JOIN ON jobs.user_id = users.id`

---

## Query Optimization Checklist

- [ ] Use EXPLAIN ANALYZE to check if indexes are used
- [ ] Avoid functions on indexed columns
- [ ] Use composite indexes for multi-column filters
- [ ] Add LIMIT for large result sets
- [ ] Use appropriate data types (avoid implicit conversions)
- [ ] Monitor slow query logs
- [ ] Update table statistics regularly: `ANALYZE table_name;`

---

**Created**: 2025-10-29
**Migration**: `173e95521004_add_performance_indexes`

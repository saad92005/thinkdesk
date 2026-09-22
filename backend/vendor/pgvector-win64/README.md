# pgvector v0.8.0 — precompiled for this machine's PostgreSQL 16

Built from source against `C:\Program Files\PostgreSQL\16` using the
Visual Studio 2022 Build Tools C++ toolchain already installed on this
machine. Installing it requires copying files into `Program Files`, which
needs an elevated (Run as Administrator) PowerShell — something this
Claude Code session cannot do itself.

## To finish installing it

Run in an **elevated** PowerShell:

```powershell
Copy-Item "E:\thinkdesk\backend\vendor\pgvector-win64\vector.dll" "C:\Program Files\PostgreSQL\16\lib\"
Copy-Item "E:\thinkdesk\backend\vendor\pgvector-win64\vector.control" "C:\Program Files\PostgreSQL\16\share\extension\"
Copy-Item "E:\thinkdesk\backend\vendor\pgvector-win64\vector--0.8.0.sql" "C:\Program Files\PostgreSQL\16\share\extension\"
```

Then enable it in the database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Once that's done, retrieval can switch from the Python cosine-similarity
fallback (`app/retrieval/vector_store.py`) to a native `vector` column with
an HNSW index, without changing the service-layer API — see
`docs/architecture.md`.

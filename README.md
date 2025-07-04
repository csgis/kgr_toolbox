### SQL Commands for Template Creation

When creating a clean template from a database, the plugin executes the following SQL commands in sequence:

#### 1. Disconnect Active Users
```sql
-- Terminate all active connections to the source database
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'source_database_name' 
  AND pid != pg_backend_pid();
```

#### 2. Create Template Database (Full Copy with Template Flag)
```sql
-- Drop existing template if it exists
DROP DATABASE "template_database_name";

-- Create the new template database as a complete copy of the source
-- and mark it as a template in the same command
CREATE DATABASE "template_database_name" 
WITH TEMPLATE "source_database_name" 
     IS_TEMPLATE = true;
```

#### 3. Truncate All Data from Template
```sql
-- Connect to the template database and get all user tables
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
ORDER BY schemaname, tablename;

-- Truncate each table individually with CASCADE
TRUNCATE TABLE "schema_name"."table_name" CASCADE;
```

#### 4. Template Deployment Commands
When deploying a new database from a template:
```sql
-- Drop existing database if it exists
DROP DATABASE "new_database_name";

-- Create new database from template
CREATE DATABASE "new_database_name" 
WITH TEMPLATE "template_database_name";
```

#### 5. Template Deletion Commands
When deleting a template:
```sql
-- Deactivate template status first
UPDATE pg_database 
SET datistemplate = false 
WHERE datname = 'template_database_name';

-- Drop the template database
DROP DATABASE "template_database_name";
```

### Manual Template Creation

If you prefer to create templates manually, you can use these commands directly in PostgreSQL:

```bash
# Connect to PostgreSQL
psql -h hostname -U username -d postgres

# 1. Terminate active connections to source database
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'source_database_name' 
  AND pid != pg_backend_pid();

# 2. Create template database
CREATE DATABASE "template_database_name" 
WITH TEMPLATE "source_database_name" 
     IS_TEMPLATE = true;

# 3. Connect to template database
\c template_database_name

# 4. Get list of all user tables
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
ORDER BY schemaname, tablename;

# 5. Truncate each table (repeat for each table found)
TRUNCATE TABLE "schema_name"."table_name" CASCADE;
```
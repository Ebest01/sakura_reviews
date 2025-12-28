# PostgreSQL CLI (psql) Guide for Easypanel Database

## Location
```
C:\Program Files\PostgreSQL\18\bin\psql.exe
```

## Connection String
```
Host: 193.203.165.217
Port: 5432
Database: sakrev_db
Username: saksaks
Password: 11!!!!.Magics4321
```

## Quick Commands

### 1. Connect to Database
```bash
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 193.203.165.217 -p 5432 -U saksaks -d sakrev_db
```

### 2. View All Tables (from command line)
```bash
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 193.203.165.217 -p 5432 -U saksaks -d sakrev_db -c "\dt"
```

### 3. View Table Structure
```bash
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 193.203.165.217 -p 5432 -U saksaks -d sakrev_db -c "\d shops"
```

### 4. Query Data from Table
```bash
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 193.203.165.217 -p 5432 -U saksaks -d sakrev_db -c "SELECT * FROM shops;"
```

## Interactive Mode Commands

Once connected interactively, use these commands:

- `\dt` - List all tables
- `\d table_name` - Describe table structure
- `\du` - List all users
- `\l` - List all databases
- `\q` - Quit
- `\?` - Show help

## Examples

### View all tables:
```
\dt
```

### View shops table data:
```
SELECT * FROM shops;
```

### View reviews table structure:
```
\d reviews
```

### Count rows in each table:
```
SELECT 'shops' as table_name, COUNT(*) FROM shops
UNION ALL
SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL
SELECT 'imports', COUNT(*) FROM imports
UNION ALL
SELECT 'settings', COUNT(*) FROM settings;
```

with open("pipeline_log.txt", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

print(f"Total lines in log: {len(lines)}")
print("--- LAST 50 LINES ---")
for line in lines[-50:]:
    print(line.strip())

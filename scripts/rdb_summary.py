import sys, klayout.rdb as rdb
db = rdb.ReportDatabase(""); db.load(sys.argv[1])
tot = 0
for cat in db.each_category():
    n = cat.num_items()
    if n: print(f"{n:6d}  {cat.name()}"); tot += n
print("TOTAL", tot)

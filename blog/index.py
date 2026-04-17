import os, json, glob
posts = sorted(glob.glob('/root/workspace/Penelope/blog/posts/*.json'), reverse=True)
items = []
for p in posts[:50]:
    try:
        items.append(json.loads(open(p).read()))
    except:
        pass
print(json.dumps(items))

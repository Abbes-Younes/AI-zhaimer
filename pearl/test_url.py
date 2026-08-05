import requests

GRAPHQL_URL = "https://openneuro.org/crn/graphql"

# Test 1: Get latest tag
q1 = '{ dataset(id: "ds004796") { snapshots { tag } } }'
r1 = requests.post(GRAPHQL_URL, json={"query": q1}, timeout=15)
print("Status:", r1.status_code)
data1 = r1.json()
snapshots = data1.get("data", {}).get("dataset", {}).get("snapshots", [])
print("Snapshots:", snapshots)

if snapshots:
    tag = snapshots[0]["tag"]
    print(f"Latest tag: {tag}")

    # Test 2: Get file listing
    q2 = """
    query {
      snapshot(datasetId: "ds004796", tag: "%s") {
        files {
          filename
          size
          directory
          urls
        }
      }
    }
    """ % tag
    r2 = requests.post(GRAPHQL_URL, json={"query": q2}, timeout=30)
    data2 = r2.json()
    files = data2.get("data", {}).get("snapshot", {}).get("files", [])
    print(f"\nTotal files: {len(files)}")
    
    # Show first 5 files
    for f in files[:5]:
        print(f"  {f['filename']}: {f['size']} bytes, dirs={f['directory']}, urls={f.get('urls', [])[:1]}")
    
    # Find participants.tsv
    for f in files:
        if f["filename"] == "participants.tsv" and f.get("urls"):
            url = f["urls"][0] if isinstance(f["urls"], list) else f["urls"]
            print(f"\nDownloading participants.tsv from: {url}")
            r3 = requests.get(url, timeout=30)
            print(f"Status: {r3.status_code}, Size: {len(r3.content)}")
            if r3.status_code == 200:
                print(r3.text[:300])
            break

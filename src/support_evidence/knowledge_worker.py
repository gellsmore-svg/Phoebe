"""One fixed official source audit under an outer process deadline."""
import json
import sys
from .knowledge import corpus, fetch_source

def main():
    request=json.loads(sys.stdin.buffer.readline(4097))
    if set(request)!={"url","timeout"} or request["url"] not in {c["source"]["url"] for c in corpus()}:
        raise ValueError("unregistered documentation source")
    if not 0 < request["timeout"] <= 5:raise ValueError("source deadline")
    print(json.dumps({"source_sha256":fetch_source(request["url"],request["timeout"])}))

if __name__=="__main__":main()

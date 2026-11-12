import asyncio, sys, re
sys.path.insert(0, "/app/src")
from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema
from soar_lab.application.use_cases.alert_admission import AlertAdmissionUseCase

print("=== BUG A: severity contract API vs workflow ===")
for sev in (4, "urgent", "critical", None):
    try:
        AlertIngestSchema(severity=sev)
        print(f"  API admits severity={sev!r}")
    except Exception as e:
        print(f"  API rejects severity={sev!r}: {e}")

def wf_severity(exec_data):
    severity_raw = str(exec_data.get("severity", "")).strip()
    if not severity_raw:
        return "REJECTED: missing webhook severity"
    if re.match(r"^\d+(?:\.\d+)?$", severity_raw):
        severity = int(float(severity_raw))
    else:
        m = {"low":1,"medium":2,"high":3,"critical":3,"info":1,"warning":2}
        severity = m.get(severity_raw.lower(), 0)
    if severity < 1 or severity > 3:
        return f"REJECTED: severity out of range: {severity_raw}"
    return f"accepted severity={severity}"

for sev in (4, "urgent", "critical", None):
    print(f"  workflow severity={sev!r} -> {wf_severity({'severity': sev})}")

print()
print("=== BUG B: orphan admission record when enqueue fails ===")
class FailQueue:
    async def depth(self): return 0
    async def enqueue(self, e): raise ConnectionError("redis down")
class Store:
    def __init__(self): self.records={}; self.by_key={}
    async def create(self, r): self.records[r["admission_id"]]=dict(r)
    async def update(self,a,f): self.records[a].update(f)
    async def get(self,a): return self.records.get(a)
    async def try_bind_key(self,k,a):
        if k in self.by_key: return self.by_key[k]
        self.by_key[k]=a; return None
    async def unbind_key(self,k,a):
        if self.by_key.get(k)==a: del self.by_key[k]

async def main():
    st = Store()
    uc = AlertAdmissionUseCase(queue=FailQueue(), store=st)
    try:
        await uc.admit({"alert_id": "a1", "severity": 2})
    except ConnectionError as e:
        print("  admit raised:", e)
    print("  store records after failure:", st.records)
    print("  by_key after failure:", st.by_key)
    print("  -> record stays 'queued' forever (recover() only reclaims QUEUE entries)")

    print()
    print("=== BUG C: idempotent replay returns phantom admission ===")
    st2 = Store(); st2.by_key["k1"] = "adm-lost"
    class OkQ:
        async def depth(self): return 0
        async def enqueue(self, e): return "e1"
    uc2 = AlertAdmissionUseCase(queue=OkQ(), store=st2)
    res = await uc2.admit({"idempotency_key": "k1", "severity": 2})
    print("  admit returned:", res)
    print("  status('adm-lost') ->", await uc2.status("adm-lost"), "(HTTP layer => 404)")

asyncio.run(main())

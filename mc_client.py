
import httpx
MC_URL="http://localhost:3000"
def get(path):
    try: return httpx.get(f"{MC_URL}{path}",timeout=15).json()
    except Exception as e: return {"error":str(e)}
def post(path,data):
    try: return httpx.post(f"{MC_URL}{path}",json=data,timeout=15).json()
    except Exception as e: return {"error":str(e)}
def patch(path,data):
    try: return httpx.request("PATCH",f"{MC_URL}{path}",json=data,timeout=15).json()
    except Exception as e: return {"error":str(e)}
def log(content,topic="business",important=False):
    post("/api/journal",{"content":content,"topic":topic,"important":important})
def queue_approval(title,type_,description,deliverable,cost=0,roi="",free_tried=None):
    return post("/api/approvals",{"action":"submit","payload":{"title":title,"type":type_,"description":description,"deliverable":deliverable,"cost":cost,"expected_roi":roi,"free_alternatives_tried":free_tried or []}})
def add_pipeline_lead(name,source,estimated_value,stage="prospect"):
    return post("/api/revenue",{"action":"add_pipeline","payload":{"name":name,"source":source,"estimated_value":estimated_value,"stage":stage}})
def get_revenue(): return get("/api/revenue")
def get_pending_approvals():
    r=get("/api/approvals"); return [a for a in r if a.get("status")=="pending"] if isinstance(r,list) else []
def get_today_journal():
    import datetime; today=datetime.date.today().isoformat()
    r=get(f"/api/journal/{today}"); return r.get("entries",[]) if isinstance(r,dict) else []
def already_ran_today(task_name):
    return any(task_name.lower() in e.get("content","").lower() for e in get_today_journal())


import datetime,time,threading,json
from pathlib import Path
import mc_client,groq_client,keys_manager,tasks

class SupermanProtocol:
    def __init__(self): self.send_fn=None; self.running=False; self.cycle_count=0; self.last_actions=[]
    def start(self,send_fn=None):
        self.send_fn=send_fn; self.running=True
        t=threading.Thread(target=self._loop,daemon=True,name="superman")
        t.start()
        mc_client.log("Superman Protocol activated. Penelope is autonomous.",topic="business",important=True)
        return t
    def stop(self): self.running=False
    def _send(self,msg):
        if self.send_fn:
            try: self.send_fn(msg)
            except: pass
    def _scan(self):
        rev=mc_client.get_revenue(); pending=mc_client.get_pending_approvals()
        new_docs=[]
        proc_log=Path("/home/penelope/app/processed_docs.json")
        processed=set(json.loads(proc_log.read_text()) if proc_log.exists() else [])
        for d in [Path("/home/penelope/docs/raw")]:
            if d.exists():
                for f in d.glob("*.*"):
                    if f.name not in processed: new_docs.append(str(f))
        return {"hour":datetime.datetime.now().hour,"revenue":rev,"earned":rev.get("total_earned",0),"goal":rev.get("monthly_goal",10000),"gap":rev.get("monthly_goal",10000)-rev.get("total_earned",0),"pending_count":len(pending),"available_keys":keys_manager.status(),"new_docs":new_docs}
    def _reason(self,state):
        actions=[]; hour=state["hour"]; has_apify=state["available_keys"].get("APIFY_API_KEY",False)
        if state["new_docs"]: actions.append(("process_doc",{"path":state["new_docs"][0]}))
        if hour==8 and not mc_client.already_ran_today("morning briefing"): actions.append(("morning_briefing",{}))
        if hour==9 and has_apify: actions.append(("callux_lead_gen",{}))
        if state["gap"]>5000 and has_apify and hour in [11,14] and not mc_client.already_ran_today("callux lead gen"): actions.append(("callux_lead_gen",{}))
        if hour==15 and datetime.date.today().day%3==0: actions.append(("app_factory",{}))
        if hour==21 and not mc_client.already_ran_today("evening summary"): actions.append(("evening_summary",{}))
        if not actions: actions.append(("pipeline_check",{}))
        return actions
    def _execute(self,action,params):
        if action=="morning_briefing": return {"done":True,"preview":tasks.morning_briefing(self.send_fn)[:80]}
        if action=="evening_summary": return {"done":True,"preview":tasks.evening_summary(self.send_fn)[:80]}
        if action=="callux_lead_gen": return tasks.callux_lead_gen(params.get("city"))
        if action=="app_factory": return tasks.app_factory_cycle()
        if action=="process_doc":
            path=params["path"]
            try:
                content=Path(path).read_text(errors="ignore")[:4000]
                intel=groq_client.complete_json("Extract actionable intel from doc. JSON only.",f'Document: {content}\nReturn: {{"summary":"str","next_steps":["str"],"revenue_opportunity":"str or null"}}')
                mc_client.log(f"Doc read: {Path(path).name}. Steps: {str(intel.get('next_steps',[]))[:200]}",topic="business",important=bool(intel.get("revenue_opportunity")))
                proc_log=Path("/home/penelope/app/processed_docs.json")
                processed=set(json.loads(proc_log.read_text()) if proc_log.exists() else [])
                processed.add(Path(path).name)
                proc_log.write_text(json.dumps(list(processed)))
                return {"processed":path}
            except Exception as e: return {"error":str(e)}
        if action=="pipeline_check":
            rev=mc_client.get_revenue(); prospects=[p for p in rev.get("pipeline",[]) if p.get("stage")=="prospect"]
            if prospects: mc_client.log(f"Pipeline: {len(prospects)} prospects active",topic="business")
            return {"prospects":len(prospects) if prospects else 0}
        return {"skipped":True}
    def _loop(self):
        while self.running:
            try:
                self.cycle_count+=1
                state=self._scan(); actions=self._reason(state)
                for action,params in actions:
                    try:
                        result=self._execute(action,params)
                        self.last_actions.append({"time":datetime.datetime.now().isoformat()[:16],"action":action,"result":str(result)[:100]})
                    except Exception as e: mc_client.log(f"Task error [{action}]: {e}",topic="business")
                self.last_actions=self.last_actions[-50:]
            except Exception as e: mc_client.log(f"Protocol error: {e}",topic="business")
            time.sleep(1800)
    def status(self): return {"running":self.running,"cycles":self.cycle_count,"last_actions":self.last_actions[-5:]}

protocol=SupermanProtocol()
def start(send_fn=None): return protocol.start(send_fn)
def get_status(): return protocol.status()

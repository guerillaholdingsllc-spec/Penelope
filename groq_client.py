
import httpx,json,re
import keys_manager
ENDPOINT="https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL="llama3-70b-8192"
def complete(system,user,max_tokens=1500,model=DEFAULT_MODEL):
    key=keys_manager.get("GROQ_API_KEY")
    if not key: return "ERROR: GROQ_API_KEY not set"
    try:
        r=httpx.post(ENDPOINT,headers={"Authorization":f"Bearer {key}"},json={"model":model,"max_tokens":max_tokens,"messages":[{"role":"system","content":system},{"role":"user","content":user}]},timeout=45)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e: return f"Groq error: {e}"
def complete_json(system,user,max_tokens=1500):
    raw=complete(system,user,max_tokens=max_tokens)
    try: return json.loads(re.sub(r"```json|```","",raw).strip())
    except: return {}
def fast(user,max_tokens=500):
    return complete("You are a direct concise assistant.",user,max_tokens=max_tokens,model="llama3-8b-8192")

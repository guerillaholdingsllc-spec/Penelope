#!/usr/bin/env python3
"""
ADD THESE ROUTES TO /root/workspace/Penelope/api.py
Paste after the existing /feed route.
"""

# ── Paste this block into api.py ──────────────────────────────────────────────

TRADING_STATE_FILE = "/root/workspace/Penelope/trading_bot/engine_v3_state.json"

@app.route("/status", methods=["GET"])
def trading_status():
    """
    Read-only trading engine status endpoint.
    Mirrors go-trader's localhost:8099/status format.
    No auth required — read-only.
    """
    import json, os, datetime
    try:
        if not os.path.exists(TRADING_STATE_FILE):
            return app.response_class(
                json.dumps({"error": "Engine v3 state not found. Start penelope_trading_engine.py first."}),
                mimetype="application/json", status=404
            )
        state = json.loads(open(TRADING_STATE_FILE).read())
        strategies_out = {}
        total_capital = 0
        total_value = 0

        for sid, st in state.items():
            if sid == "_meta":
                continue
            if not isinstance(st, dict):
                continue
            strategies_out[sid] = {
                "portfolio_value":    st.get("portfolio_value", 0),
                "initial_capital":    st.get("initial_capital", 0),
                "pnl":                st.get("pnl", 0),
                "pnl_pct":            st.get("pnl_pct", 0),
                "trade_count":        st.get("trade_count", 0),
                "win_count":          st.get("win_count", 0),
                "consecutive_losses": st.get("consecutive_losses", 0),
                "position":           st.get("position"),
                "risk_state":         st.get("risk_state", {}),
            }
            total_capital += st.get("initial_capital", 0)
            total_value   += st.get("portfolio_value", 0)

        total_pnl = total_value - total_capital
        cb_active = 0
        for st in strategies_out.values():
            until = st.get("risk_state", {}).get("circuit_breaker_until")
            if until:
                try:
                    if datetime.datetime.now() < datetime.datetime.fromisoformat(until):
                        cb_active += 1
                except:
                    pass

        ranked = sorted(strategies_out.items(), key=lambda x: x[1]["pnl_pct"], reverse=True)
        top5   = [{"id": k, **v} for k, v in ranked[:5]]
        bottom5= [{"id": k, **v} for k, v in ranked[-5:]]
        dead   = [k for k, v in strategies_out.items() if v["trade_count"] == 0]

        payload = {
            "timestamp":    datetime.datetime.now().isoformat(),
            "cycle_count":  state.get("_meta", {}).get("cycle_count", 0),
            "started":      state.get("_meta", {}).get("started"),
            "summary": {
                "total_capital":          total_capital,
                "total_value":            round(total_value, 2),
                "total_pnl":              round(total_pnl, 2),
                "total_pnl_pct":          round((total_pnl / total_capital * 100) if total_capital else 0, 2),
                "strategies_count":       len(strategies_out),
                "circuit_breakers_active": cb_active,
                "dead_strategies":        len(dead),
            },
            "top5":       top5,
            "bottom5":    bottom5,
            "dead":       dead,
            "strategies": strategies_out,
        }
        return app.response_class(
            json.dumps(payload, indent=2),
            mimetype="application/json"
        )
    except Exception as e:
        return app.response_class(
            json.dumps({"error": str(e)}),
            mimetype="application/json", status=500
        )

import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

SERVER_STATE = {"value": None, "type": None}
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/aggregate", methods=["POST"])
def aggregate():
   
    body = request.get_json(silent=True) or {}
    protocol = body.get("protocol")
    records = body.get("records") or []

    if protocol not in ("secure", "standard"):
        return jsonify({"error": "protocol must be 'secure' or 'standard'"}), 400
    if not records:
        return jsonify({"error": "No records to process"}), 400

    logs = []
    count = len(records)

    try:
        if protocol == "standard":
            total = 0
            for r in records:
                val = int(r["value"])
                total += val
                logs.append({
                    "step": "RECV",
                    "detail": f"{r.get('name', 'record')} · plaintext salary {val} received in the clear",
                })
            SERVER_STATE["value"] = str(total)
            SERVER_STATE["type"] = "PLAINTEXT_LEAK"

            return jsonify({
                "logs": logs,
                "mode": "standard",
                "total": total,
                "count": count,
                "average": round(total / count, 2),
            })

        # --- secure: homomorphic addition on ciphertexts only ---
        n_str = body.get("n")
        if not n_str:
            return jsonify({"error": "Missing public modulus 'n'"}), 400
        n = int(n_str)
        n_sq = n * n

        encrypted_sum = 1  # multiplicative identity mod n^2
        for r in records:
            c = int(r["value"])
            encrypted_sum = (encrypted_sum * c) % n_sq
            short = str(c)[:18] + "…"
            logs.append({
                "step": "RECV",
                "detail": f"{r.get('name', 'record')} · ciphertext {short} (encrypted in the browser)",
            })

        logs.append({
            "step": "FOLD",
            "detail": "Homomorphic product computed mod n² — no decryption performed server-side",
        })

        SERVER_STATE["value"] = str(encrypted_sum)
        SERVER_STATE["type"] = "SECURE_CIPHERTEXT"

        return jsonify({
            "logs": logs,
            "mode": "secure",
            "encrypted_sum": str(encrypted_sum),
            "count": count,
        })

    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Malformed record data: {e}"}), 400


@app.route("/api/hack_attempt", methods=["POST"])
def hack_attempt():

    if not SERVER_STATE["value"]:
        return jsonify({"status": "empty"})
    return jsonify({
        "status": "success",
        "type": SERVER_STATE["type"],
        "data": SERVER_STATE["value"],
    })


if __name__ == "__main__":
    os.makedirs("templates", exist_ok=True)
    debug_mode = os.environ.get("FLASK_DEBUG") == "1"
    app.run(debug=debug_mode, port=5000)

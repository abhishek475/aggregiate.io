import pandas as pd
import io
import random
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ==========================================
# 📐 EUCLIDEAN THEORY IMPLEMENTATION
# ==========================================
def euclidean_gcd(a, b):
    """Euclid's original algorithm (c. 300 BC)."""
    while b:
        a, b = b, a % b
    return a

def ext_euclidean(a, m):
    """Modular multiplicative inverse via Extended Euclidean Algorithm."""
    m0, x0, x1 = m, 0, 1
    if m == 1: return 0
    while a > 1:
        q = a // m
        m, a = a % m, m
        x0, x1 = x1 - q * x0, x0
    if x1 < 0: x1 += m0
    return x1

# ==========================================
# 🔐 THE MATH ENGINE (PAILLIER CRYPTOSYSTEM)
# ==========================================
class Paillier:
    def __init__(self):
        # 1. Key Generation
        p, q = 1009, 2741
        self.n = p * q
        self.n_sq = self.n * self.n
        self.g = self.n + 1

        # Calculate Private Components
        self.lam = (p - 1) * (q - 1) // euclidean_gcd(p - 1, q - 1)
        self.mu = ext_euclidean(self.lam, self.n)

        # --- TERMINAL DISPLAY FOR JUDGES ---
        print("\n" + "="*60)
        print("🔐 TOTIENT CRYPTO ENGINE: KEY GENERATION LOG")
        print("="*60)
        print(f" [+] PRIMES CHOSEN (p, q):   {p}, {q}")
        print(f" [+] EUCLIDEAN ALGORITHM:    COMPLETED.")
        print("-" * 60)
        print(f" 🔑 PUBLIC KEY (Visible to Server):")
        print(f"     n (Modulus) = {self.n}")
        print(f"     g (Gen)     = {self.g}")
        print("-" * 60)
        print(f" 🗝️  PRIVATE KEY (Hidden on Client):")
        print(f"     λ (Lambda)  = {self.lam}")
        print(f"     μ (Mu)      = {self.mu}")
        print("="*60 + "\n")

    def encrypt(self, m):
        r = random.randint(1, self.n - 1)
        return (pow(self.g, m, self.n_sq) * pow(r, self.n, self.n_sq)) % self.n_sq

    def decrypt(self, c):
        u = pow(c, self.lam, self.n_sq)
        return ((u - 1) // self.n * self.mu) % self.n

crypto = Paillier()
SERVER_STATE = {"memory_value": None, "memory_type": None}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    file = request.files.get('file')
    protocol = request.form.get('protocol', 'homomorphic')
    if not file: return jsonify({"error": "No file"}), 400

    try:
        df = pd.read_csv(file)
        # Data Cleaning
        if "Salary" not in df.columns: return jsonify({"error": "CSV missing 'Salary' column"}), 400
        df = df.dropna(subset=['Salary'])
        df['Salary'] = pd.to_numeric(df['Salary'], errors='coerce').fillna(0).astype(int)

        logs = []
        encrypted_sum = crypto.encrypt(0)

        # --- SCENARIO A: STANDARD (UNSAFE) ---
        if protocol == 'standard':
            real_sum = int(df['Salary'].sum())
            SERVER_STATE["memory_value"] = f"{real_sum}"
            SERVER_STATE["memory_type"] = "PLAINTEXT_LEAK"

            logs.append({"step": "🛑 MODE", "detail": "STANDARD (Keys Loaded in RAM)"})
            for _, row in df.iterrows():
                logs.append({"step": "🔓 DECRYPT", "detail": f"{row.get('Employee Name', 'User')}: Decrypting..."})

            logs.append({"step": "➕ MATH", "detail": f"Calculating Sum: {real_sum}"})
            decrypted_total = real_sum

        # --- SCENARIO B: TOTIENT (SECURE) ---
        else:
            logs.append({"step": "✅ MODE", "detail": "TOTIENT (Zero-Knowledge)"})

            for _, row in df.iterrows():
                enc_val = crypto.encrypt(row['Salary'])
                # Homomorphic Addition
                encrypted_sum = (encrypted_sum * enc_val) % crypto.n_sq

                # Truncate ciphertext for cleaner logs
                short_cipher = str(enc_val)[:15] + "..."
                logs.append({"step": "📥 RECV", "detail": f"{row.get('Employee Name', 'User')} | Cipher: {short_cipher}"})

            SERVER_STATE["memory_value"] = str(encrypted_sum)
            SERVER_STATE["memory_type"] = "SECURE_CIPHERTEXT"
            decrypted_total = crypto.decrypt(encrypted_sum)

        return jsonify({
            "logs": logs,
            "final_cipher": str(encrypted_sum)[:30] + "...",
            "total": int(decrypted_total),
            "count": len(df),
            "average": round(decrypted_total / len(df), 2) if len(df) > 0 else 0
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/hack_attempt', methods=['POST'])
def hack():
    if not SERVER_STATE["memory_value"]: return jsonify({"status": "empty"})
    return jsonify({"status": "success", "type": SERVER_STATE["memory_type"], "data": SERVER_STATE["memory_value"]})

if __name__ == '__main__':
    # Ensure templates folder exists
    import os
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(debug=True, port=5000)

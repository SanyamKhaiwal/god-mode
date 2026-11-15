"""Hidden check for H1 (numpy transformer). Uses its OWN gradient check and the reference training script,
so a run can't pass by editing gradcheck.py or train.py. Usage: python -I hidden_ml.py <repo_dir>"""
import importlib.util
import os
import sys

import numpy as np

REPO = sys.argv[1]
REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


model = load("model", os.path.join(REPO, "model.py"))
train = load("train", os.path.join(REF, "train.py"))  # reference task + optimizer, imports the run's model

checks = []


def chk(name, ok):
    checks.append((name, bool(ok)))


# 1. gradients: every parameter, central differences in float64
rng = np.random.default_rng(7)
p = model.init_params(train.VOCAB, 8, 16, train.T, seed=3)
x, y, mask = train.batch(rng, 3)
_, _, cache = model.forward(p, x, y, mask)
g = model.backward(p, cache)
for name in model.PARAMS:
    flat = p[name].reshape(-1)
    idx = rng.choice(flat.size, size=min(30, flat.size), replace=False)
    num = []
    for i in idx:
        old = flat[i]
        flat[i] = old + 1e-6; lp = model.forward(p, x, y, mask)[1]
        flat[i] = old - 1e-6; lm = model.forward(p, x, y, mask)[1]
        flat[i] = old
        num.append((lp - lm) / 2e-6)
    a, n = g[name].reshape(-1)[idx], np.array(num)
    err = np.abs(a - n).max() / max(1e-8, np.abs(a).max() + np.abs(n).max())
    chk(f"gradient {name} (rel err {err:.1e})", err < 1e-5)

# 2. causality: changing tokens at positions > t must not change the logits at positions <= t
p2 = model.init_params(train.VOCAB, 16, 32, train.T, seed=5)
base = np.random.default_rng(1).integers(1, train.VOCAB, size=(4, train.T))
leak = 0.0
for t in range(train.T - 1):
    alt = base.copy()
    alt[:, t + 1:] = (alt[:, t + 1:] % (train.VOCAB - 1)) + 1  # change every future token
    la = model.forward(p2, base)[0][:, : t + 1]
    lb = model.forward(p2, alt)[0][:, : t + 1]
    leak = max(leak, float(np.abs(la - lb).max()))
chk(f"causal: no information flows from future tokens (max change {leak:.1e})", leak < 1e-9)

# 3. learning still works end to end with the reference training loop
params, loss = train.train(steps=800, seed=0, verbose=False)
acc = train.copy_accuracy(params)
chk(f"trains: greedy copy accuracy {acc:.3f} >= 0.95", acc >= 0.95)

for n_, ok in checks:
    print(("PASS " if ok else "FAIL ") + n_)
print(f"{sum(ok for _, ok in checks)}/{len(checks)}")

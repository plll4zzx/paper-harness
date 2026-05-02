# Minimal PyTorch Repo

Install:

```bash
pip install -r requirements.txt
```

Train a small CIFAR-10 model:

```bash
python train.py --config configs/cifar10.yaml
```

Evaluate:

```bash
python evaluate.py --checkpoint outputs/best.pt
```

This repository intentionally does not expose every paper hyperparameter name.

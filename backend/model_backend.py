import os
import numpy as np
import torch
import torch.nn as nn

BACKEND = os.getenv("MODEL_BACKEND", "torch").lower()
MODEL_PATH = os.getenv("MODEL_PATH", "soc_model.pth")
SEQ_LEN = int(os.getenv("SEQ_LEN", "15"))

# -------- Basit LSTM mimarisi (state_dict için) --------
class LSTMNet(nn.Module):
    def __init__(self, input_size=3, hidden_size=32, num_layers=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):  # x: (B,T,3)
        out, _ = self.lstm(x)
        y = self.fc(out[:, -1, :])
        return y

# -------- Dummy Model (yedek) --------
class DummyModel:
    def predict_point(self, x_row):
        v, i, t = x_row
        soc = (v - 3.0) / (4.2 - 3.0) * 100.0
        return float(np.clip(soc, 0, 100))

    def predict_sequence(self, x_seq):
        return self.predict_point(x_seq[-1])

# -------- Torch Model Loader --------
class TorchLSTMModel:
    def __init__(self, path):
        self.device = "cpu"
        ckpt = torch.load(path, map_location=self.device)

        if isinstance(ckpt, nn.Module):
            self.model = ckpt
        elif isinstance(ckpt, dict):
            self.model = LSTMNet()
            try:
                self.model.load_state_dict(ckpt, strict=False)
            except Exception:
                if "state_dict" in ckpt:
                    self.model.load_state_dict(ckpt["state_dict"], strict=False)
                else:
                    raise
        else:
            raise RuntimeError("Desteklenmeyen .pth formatı")

        self.model.eval()

    def predict_sequence(self, x_seq):
        t = torch.tensor(x_seq, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            y = self.model(t).squeeze().item()
        return float(np.clip(y, 0, 100))

    def predict_point(self, x_row):
        arr = np.array(x_row, dtype=np.float32).reshape(1, 1, 3)
        return self.predict_sequence(arr[0])

# -------- Factory --------
def load_backend():
    if BACKEND == "torch":
        try:
            return TorchLSTMModel(MODEL_PATH)
        except Exception as e:
            print(f"[WARN] Model yüklenemedi ({e}), Dummy modele düşüldü.")
            return DummyModel()
    return DummyModel()

# %%
import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModel
from tqdm.auto import tqdm

SEED = 42
torch.manual_seed(SEED)

MODEL_NAME = ""
MAX_LEN = 128
BATCH_SIZE = 32
EPOCHS = 3
LR = 2e-5

if os.path.basename(os.getcwd()).lower() == "trained":
    WEIGHTS_DIR = os.path.abspath(os.path.join(os.getcwd(), "..", "weights"))
else:
    WEIGHTS_DIR = os.path.abspath(os.path.join("models", "weights"))
os.makedirs(WEIGHTS_DIR, exist_ok=True)
OUTPUT_PTH = os.path.join(WEIGHTS_DIR, "bert_tiny_sentiment.pth")
print("Weights path:", OUTPUT_PTH)

# %%
device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# %%
class TinyBertSentiment(nn.Module):
    def __init__(self, model_name=MODEL_NAME, dropout=0.2):
        super().__init__()
        self.backbone = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(self.backbone.config.hidden_size, 2)

    def forward(self, input_ids, attention_mask):
        out = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
        cls_token = out.last_hidden_state[:, 0, :]  # [CLS]
        logits = self.classifier(self.dropout(cls_token))
        return logits


def tokenize_batch(batch):
    return tokenizer(
        batch["text"],
        padding="max_length",
        truncation=True,
        max_length=MAX_LEN,
    )


model = TinyBertSentiment().to(device)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.AdamW(model.parameters(), lr=LR)

# %%
def train_one_epoch(model, loader, optimizer, criterion, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for batch in tqdm(loader, desc="Training", leave=False):
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["label"].to(device)

        optimizer.zero_grad()
        logits = model(input_ids, attention_mask)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * labels.size(0)
        preds = logits.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    return running_loss / total, correct / total


def evaluate(model, loader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for batch in tqdm(loader, desc="Evaluating", leave=False):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["label"].to(device)

            logits = model(input_ids, attention_mask)
            loss = criterion(logits, labels)

            running_loss += loss.item() * labels.size(0)
            preds = logits.argmax(dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

    return running_loss / total, correct / total


if os.path.exists(OUTPUT_PTH):
    model.load_state_dict(torch.load(OUTPUT_PTH, map_location=device))
    model.eval()
    size_mb = os.path.getsize(OUTPUT_PTH) / (1024 * 1024)
    print(f"Loaded existing weights from: {OUTPUT_PTH} | Size: {size_mb:.2f} MB")
else:
    print("No saved weights found. Starting training...")

    dataset = load_dataset("imdb")

    train_ds = dataset["train"].shuffle(seed=SEED).select(range(20000))
    test_ds = dataset["test"].shuffle(seed=SEED).select(range(5000))

    train_ds = train_ds.map(tokenize_batch, batched=True)
    test_ds = test_ds.map(tokenize_batch, batched=True)

    cols = ["input_ids", "attention_mask", "label"]
    train_ds.set_format(type="torch", columns=cols)
    test_ds.set_format(type="torch", columns=cols)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)
    print("Train batches:", len(train_loader), "| Test batches:", len(test_loader))

    for epoch in range(1, EPOCHS + 1):
        train_loss, train_acc = train_one_epoch(model, train_loader, optimizer, criterion, device)
        val_loss, val_acc = evaluate(model, test_loader, criterion, device)

        print(
            f"Epoch {epoch}/{EPOCHS} | "
            f"train_loss={train_loss:.4f}, train_acc={train_acc:.4f} | "
            f"val_loss={val_loss:.4f}, val_acc={val_acc:.4f}"
        )
    torch.save(model.state_dict(), OUTPUT_PTH)
    size_mb = os.path.getsize(OUTPUT_PTH) / (1024 * 1024)
    print(f"Saved: {OUTPUT_PTH} | Size: {size_mb:.2f} MB")

    if size_mb >= 100:
        print("Warning: model is >= 100MB. Consider reducing MAX_LEN or using fewer parameters.")
    else:
        print("Success: model size is under 100MB.")


def predict_sentiment(text, model, tokenizer, device, max_len=MAX_LEN):
    model.eval()
    enc = tokenizer(
        text,
        max_length=max_len,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )

    input_ids = enc["input_ids"].to(device)
    attention_mask = enc["attention_mask"].to(device)

    with torch.no_grad():
        logits = model(input_ids, attention_mask)
        probs = torch.softmax(logits, dim=1).squeeze(0)
        pred = torch.argmax(probs).item()

    label = "positive" if pred == 1 else "negative"
    confidence = probs[pred].item()
    return label, confidence

sample = "Can you just shut the fuck up"
label, conf = predict_sentiment(sample, model, tokenizer, device)
print(f"Text: {sample}\nPrediction: {label} ({conf:.4f})")

# %%
reloaded_model = TinyBertSentiment().to(device)
reloaded_model.load_state_dict(torch.load(OUTPUT_PTH, map_location=device))
reloaded_model.eval()

text = "I did not like the product, it broke on day one."
label, conf = predict_sentiment(text, reloaded_model, tokenizer, device)
print(f"Reloaded model prediction: {label} ({conf:.4f})")
print("Loaded from:", OUTPUT_PTH)

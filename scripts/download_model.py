"""Pre-download Paraformer model without starting the server."""
from wenet.cli.hub import Hub

print("Downloading Paraformer model (~300MB)...")
print("Target: ~/.wenet/paraformer/")
model_dir = Hub.download_model("paraformer")
print(f"Done. Model cached at: {model_dir}")

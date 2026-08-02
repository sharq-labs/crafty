import platform
import sys


def main():
    print("=" * 72)
    print("Engineering AI Core V0.2.2 — GPU Check")
    print("=" * 72)
    print("Python :", sys.version.split()[0])
    print("OS     :", platform.platform())

    try:
        import torch
    except ImportError:
        print("\nPyTorch: NOT INSTALLED")
        print("Install a CUDA-enabled PyTorch build first, then requirements-gpu.txt.")
        raise SystemExit(2)

    print("PyTorch:", torch.__version__)
    print("CUDA build:", torch.version.cuda)
    print("CUDA available:", torch.cuda.is_available())

    if not torch.cuda.is_available():
        print("\nGPU acceleration is NOT active.")
        print("The project will still run on CPU, but the GPU engine will not use your RTX.")
        raise SystemExit(3)

    print("GPU name:", torch.cuda.get_device_name(0))
    props = torch.cuda.get_device_properties(0)
    print(f"VRAM    : {props.total_memory / (1024**3):.2f} GB")
    print("Device  : cuda:0")

    # quick compute smoke test
    x = torch.randn((4096, 4096), device="cuda", dtype=torch.float32)
    y = x @ x
    torch.cuda.synchronize()
    print("CUDA matrix test: PASS")
    del x, y
    torch.cuda.empty_cache()
    print("=" * 72)


if __name__ == "__main__":
    main()

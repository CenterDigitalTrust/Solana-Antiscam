import importlib
for pkg in ["numpy", "pandas", "scipy", "sklearn", "xgboost", "lightgbm"]:
    try:
        mod = importlib.import_module(pkg)
        print(f"Package: {pkg} -> Version: {getattr(mod, '__version__', 'Installed')}")
    except ImportError:
        print(f"Package: {pkg} -> NOT INSTALLED")

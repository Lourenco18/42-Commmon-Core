import sys
import importlib
import warnings
warnings.filterwarnings("ignore")
REQUIRED_PACKAGES = ["pandas", "numpy", "matplotlib"]
# pandas → tabelas
# numpy → cálculos numéricos e arrays
# matplotlib → gráficos


def check_package(package_name):
    try:
        # Tenta importar o pacote dinamicamente
        module = importlib.import_module(package_name)
        version = getattr(module, "__version__", "unknown")
        return True, version
    except ImportError:
        return False, None


def check_dependencies():
    print("LOADING STATUS: Loading programs...")
    print("Checking dependencies:\n")

    all_ok = True

    for pkg in REQUIRED_PACKAGES:
        ok, version = check_package(pkg)

        if ok:
            print(f"[OK] {pkg} ({version}) - Ready")
        else:
            print(f"[MISSING] {pkg} - Not installed")
            all_ok = False

    return all_ok


def show_install_instructions():
    print("\nMissing dependencies detected!\n")

    print("Install with pip:")
    print("pip install -r requirements.txt\n")

    print("Install with Poetry:")
    print("poetry install\n")


def run_analysis():
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt

    print("\nAnalyzing Matrix data...")

    data_size = 1000
    print(f"Processing {data_size} data points...")

    matrix_values = np.random.randn(data_size)

    # Criar DataFrame com pandas
    df = pd.DataFrame({
        "values": matrix_values
    })

    # Criar uma média móvel (exemplo de análise)
    df["moving_avg"] = df["values"].rolling(window=50).mean()

    print("Generating visualization...")

    # Criar gráfico
    plt.figure()
    plt.plot(df["values"], label="Raw Data")
    plt.plot(df["moving_avg"], label="Moving Average")

    # Adicionar legenda
    plt.legend()

    # Guardar imagem
    output_file = "matrix_analysis.png"
    plt.savefig(output_file)

    print("Analysis complete!")
    print(f"Results saved to: {output_file}")


def show_versions():
    print("\nPackage versions (environment info):")

    for pkg in REQUIRED_PACKAGES:
        ok, version = check_package(pkg)

        if ok:
            print(f"{pkg}: {version}")
        else:
            print(f"{pkg}: NOT INSTALLED")


if __name__ == "__main__":
    deps_ok = check_dependencies()

    if not deps_ok:
        show_install_instructions()
        sys.exit(1)

    show_versions()

    run_analysis()

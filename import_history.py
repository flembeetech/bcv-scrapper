import sys
from services.db_service import import_history_from_csv

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    count = import_history_from_csv(path)
    if count > 0:
        print(f"Éxito: Se procesaron {count} registros históricos.")
    else:
        print("No se importaron registros.")

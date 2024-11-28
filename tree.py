import os

def print_tree(root, prefix='', level=0, max_depth=4):
    if max_depth is not None and level >= max_depth:
        return
    try:
        entries = os.listdir(root)
    except PermissionError:
        # Pomijamy katalogi, do których nie mamy dostępu
        return

    # Sortujemy wpisy dla czytelności
    entries = sorted(entries)

    # Oddzielamy katalogi od plików
    dirs = []
    files = []
    for entry in entries:
        path = os.path.join(root, entry)
        if os.path.isdir(path):
            dirs.append(entry)
        else:
            files.append(entry)

    # Wyświetlamy katalogi
    for idx, directory in enumerate(dirs):
        connector = '├── ' if idx < len(dirs) - 1 or files else '└── '
        print(f"{prefix}{connector}{directory}/")
        # Aktualizujemy prefiks dla podkatalogów
        extension = '│   ' if idx < len(dirs) - 1 or files else '    '
        print_tree(os.path.join(root, directory), prefix + extension, level + 1, max_depth)

    # Wyświetlamy pliki
    for idx, filename in enumerate(files):
        connector = '├── ' if idx < len(files) - 1 else '└── '
        print(f"{prefix}{connector}{filename}")

# Uruchomienie funkcji dla bieżącego katalogu
if __name__ == '__main__':
    print_tree('./rag', max_depth=4)

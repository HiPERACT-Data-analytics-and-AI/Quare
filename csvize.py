from pathlib import Path


def main():
    csvized_path = Path("../csvized")
    if not csvized_path.exists():
        csvized_path.mkdir()

    counter: int = 0
    for path in Path("..").glob("**/prof.*"):
        if "/old/" in path.as_posix():
            continue
        print(path)
        print("New path: ", Path.cwd().as_posix()[:-9] + "/csvized" + path.as_posix()[2:])
        counter += 1
    print(Path.cwd().as_posix()[:-9], counter)

if __name__ == "__main__":
    main()

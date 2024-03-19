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

def parse_csvs():
    for path in Path("data").glob("**/prof.*.csv"):
    # paths = list(Path("data").glob("**/prof.*.csv"))
    # for path in paths:
        if "parsed.csv" in path.as_posix():
            continue
        print(path)
        with open(path) as file, open(path.as_posix()[:-3] + "parsed.csv", mode="w") as out_file:
            core_metrics_flag: bool = False
            for line in file:
                if line.startswith("CORE METRICS"):
                    core_metrics_flag = True
                    continue
                if core_metrics_flag:
                    if not line.strip():
                        core_metrics_flag = False
                        continue
                    out_file.write(line)


if __name__ == "__main__":
    parse_csvs()

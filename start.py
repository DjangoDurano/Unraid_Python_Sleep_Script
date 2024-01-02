import json
import subprocess as sp
from pathlib import Path
from shutil import copy

dependencies: list = [
    "python3 /usr/lib64/python3.9/site-packages/pip install psutil",
    "python3 /usr/lib64/python3.9/site-packages/pip install ping3",
    "python3 /usr/lib64/python3.9/site-packages/pip install configobj"
]


def main():
    print('---Install dependencies.---')
    for dependency in dependencies:
        result = sp.run(dependency, shell=True, capture_output=True, text=True)
        print(result.stdout)

    print('---Backup go file and schedule.json.---')
    print('/boot/config/go -> /boot/config/go_old')
    copy("/boot/config/go", "/boot/config/go_old")
    print(r"/boot/config/plugins/user.scripts/schedule.json -> /boot/config/plugins/user.scripts/schedule_old.json")
    copy(r"/boot/config/plugins/user.scripts/schedule.json", r"/boot/config/plugins/user.scripts/schedule_old.json")

    print('---Add dependencies to go file.---')
    with open('go', "a") as f:
        f.write("\n")
        f.write("\n".join(dependencies))

    print('---Check if /boot/scripts exists.---')
    Path("/boot/scripts").mkdir(exist_ok=True)

    print('---Copy files to destination folder.---')
    copy('Python_Sleep_Script', r"/boot/config/plugins/user.scripts/scripts")
    copy("sleep.py", "/boot/scripts")
    copy("python_sleep.conf", "/boot/config")

    print('---Adding schedule for user script execution.---')
    with open(r"/boot/config/plugins/user.scripts/schedule.json", "r") as f:
        data = json.load(f)

    data["/boot/config/plugins/user.scripts/scripts/Python_Sleep_Script/script"] = {
        "script": "/boot/config/plugins/user.scripts/scripts/Python_Sleep_Script/script",
        "frequency": "start",
        "id": "schedulePython_Sleep_Script",
        "custom": "*/5 * * * *"
    }

    with open("r/boot/config/plugins/user.scripts/schedule.json", "w") as f:
        json.dump(data, f, indent=4)

    print('---Start user script.---')
    result = sp.run("/usr/local/emhttp/plugins/user.scripts/backgroundScript.sh /tmp/user.scripts/tmpScripts/Python_Sleep_Script/script",
                    shell=True, capture_output=True, text=True)
    print(result.stdout)
    print()
    print('---Finished. Set your settings in /boot/config/python_sleep.conf.---')


if __name__ == '__main__':
    main()

import json
import subprocess as sp
from pathlib import Path
from shutil import copy, copytree

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
    if Path('/boot/config/go_old').exists():
        go_name = input('Backup file "go_old" exists. Please enter alternative '
                        'name e.g. go_old2 or leave blank for no backup: ') or None
        if go_name:
            print(f'/boot/config/go -> /boot/config/{go_name}')
            copy("/boot/config/go", f"/boot/config/{go_name}")
    else:
        print('/boot/config/go -> /boot/config/go_old')
        copy("/boot/config/go", "/boot/config/go_old")
    if Path('/boot/config/plugins/user.scripts/schedule_old.json').exists():
        schedule_name = input('Backup file "schedule_old" exists. Please enter alternative '
                              'name e.g. schedule_old2 or leave blank for no backup: ') or None
        if schedule_name:
            print(fr"/boot/config/plugins/user.scripts/schedule.json -> /boot/config/plugins/user.scripts/{schedule_name}.json")
            copy(r"/boot/config/plugins/user.scripts/schedule.json", fr"/boot/config/plugins/user.scripts/{schedule_name}.json")
    else:
        print(r"/boot/config/plugins/user.scripts/schedule.json -> /boot/config/plugins/user.scripts/schedule_old.json")
        copy(r"/boot/config/plugins/user.scripts/schedule.json", r"/boot/config/plugins/user.scripts/schedule_old.json")

    print('---Add dependencies to go file.---')
    with open('/boot/config/go', "a") as f:
        f.write("\n")
        f.write("\n".join(dependencies))

    print('---Check if /boot/scripts exists.---')
    Path("/boot/scripts").mkdir(exist_ok=True)
    Path("/tmp/user.scripts/tmpScripts/Python_Sleep_Script").mkdir(exist_ok=True, parents=True, mode=16877)

    print('---Copy files to destination folder.---')
    copytree('Python_Sleep_Script', r"/boot/config/plugins/user.scripts/scripts/Python_Sleep_Script")
    copy("sleep.py", "/boot/scripts")
    copy("python_sleep.conf", "/boot/config")
    copy("Python_Sleep_Script/script", "/tmp/user.scripts/tmpScripts/Python_Sleep_Script")
    Path("/tmp/user.scripts/tmpScripts/Python_Sleep_Script/script").chmod(mode=33261)

    print('---Adding schedule for user script execution.---')
    with open(r"/boot/config/plugins/user.scripts/schedule.json", "r") as f:
        data = json.load(f)

    data["/boot/config/plugins/user.scripts/scripts/Python_Sleep_Script/script"] = {
        "script": "/boot/config/plugins/user.scripts/scripts/Python_Sleep_Script/script",
        "frequency": "start",
        "id": "schedulePython_Sleep_Script",
        "custom": "*/5 * * * *"
    }

    with open(r"/boot/config/plugins/user.scripts/schedule.json", "w") as f:
        json.dump(data, f, indent=4)

    print('---Start user script.---')
    result = sp.run("/usr/local/emhttp/plugins/user.scripts/backgroundScript.sh /tmp/user.scripts/tmpScripts/Python_Sleep_Script/script",
                    shell=True, capture_output=True, text=True)
    print(result.stdout)
    print()
    print('---Finished. Set your settings in /boot/config/python_sleep.conf.---')


if __name__ == '__main__':
    main()

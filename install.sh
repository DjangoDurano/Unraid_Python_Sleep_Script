#!/bin/bash

python=$(python3 --version 2>&1)

if [[ $python == *"No such file or directory"* ]] || [[ $python == *"python3: command not found"* ]]; then
  read -r -p "No python version found. Python is needed for working. Nerdtools python will not work.
              Choose one to install: \n 1. Python 3.9.18 (own build python by me)\n2. Python 3.12.1 (by kubed_zero)" version

  if [[ $version == 1 ]]; then
    cd /Unraid_Python_Sleep_Script/Python_Package || exit
#    upgradepkg --install-new "python3-3.9.18-x86_64-1.txz"
  else
    cd /Unraid_Python_Sleep_Script/Python_Package || exit
#    upgradepkg --install-new "python3-3.12.1-x86_64-1-kubed20231210.txz"
  fi
else
  echo $PWD
  cd /Unraid_Python_Sleep_Script || exit
  python_test=$(python3 test_python.py 2>&1)

  if [[ $python_test == "Not worked!" ]]; then
    echo "Python version don't work. Try to remove your python3 version, start script again and install python 3.9.18 own
          build or python 3.12.1 from kubed_zero. Nerdtools python3 will not work, it's not fully compatible with unraid!"
    exit
  else
    echo $PWD
  fi
fi

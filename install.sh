#!/bin/bash

echo "--- Checking python3 version ---"
python=$(python3 --version 2>&1)

if [[ $python == *"No such file or directory"* ]] || [[ $python == *"python3: command not found"* ]]; then
  read -rep $'No python version found. Python3 is needed for working. Nerdtools python3 version will not work.\n
Choose one to install: \n1. Python 3.9.18 (own python3 build by me)\n2. Python 3.12.1 (by kubed_zero)\n> ' version

  if [[ $version == 1 ]]; then
    upgradepkg --install-new "./Python_Package/python3-3.9.18-x86_64-1.txz"
    cp "./Python_Package/python3-3.9.18-x86_64-1.txz" "/boot/extra"
  else
    upgradepkg --install-new "./Python_Package/python3-3.12.1-x86_64-1-kubed20231210.txz"
    cp "./Python_Package/python3-3.12.1-x86_64-1-kubed20231210.txz" "/boot/extra"
    cp "./Python_Package/openssl-3.1.1-x86_64-1.txz" "/boot/extra"
  fi
  echo "--- Testing python3 ---"
  python_test=$(python3 test_python.py 2>&1)

    if [[ $python_test == "Not working!" ]]; then
      echo "Python version don't work. Try to remove your python3 version, start script again and install python 3.9.18 (own
build) or python 3.12.1 (from kubed_zero). Nerdtools python3 will not work, it's not fully compatible with unraid!"
      exit
    else
      echo "> Python3 is working."
      echo "--- Installing script ---"
      python3 start.py
    fi
else
  echo "--- Testing python3 ---"
  python_test=$(python3 test_python.py 2>&1)

  if [[ $python_test == "Not working!" ]]; then
    echo "Python version don't work. Try to remove your python3 version, start script again and install python 3.9.18 (own
build) or python 3.12.1 (from kubed_zero). Nerdtools python3 will not work, it's not fully compatible with unraid!"
    exit
  else
    echo "> Python3 is working."
    echo "--- Installing script ---"
    python3 start.py
  fi
fi

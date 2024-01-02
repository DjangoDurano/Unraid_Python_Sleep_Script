# Description:

A python script, that has nearly the same functions as the original sleep plugin for unraid. It can replace the original plugin complete. The original plugin don't work for me in any way, so I decided to make my own script with python.


### Advantages:
- more functionality
- not depend on any unraid version, needs only python to work
- maintaining is easier, if you can write python code you can fix it, no need to know how plugins work

### Disadvantages:
- not fancy gui to set your settings, you must set your settings in a config file
- no additional commands before/after sleeps

### Functions:
- can detect disk activity from (array, cache, unassigned)
- can detect ethernet activity, choose your preferred interface, multiple interfaces possible
- can detect smb traffic, works similar to active streams' plugin, can detect all smb traffic, or you can choose specific shares to watch (user shares or disk shares)
- can detect host activity, multiple hosts are possible
- can detect user activity, remote user only, local user activity don't work
- checks at startup automatically if there are new disks, ethernet interfaces, shares and add these to the config file, you can also set a timer to do this after some time again
- waits for array startup at script startup
- script execution can be stopped from config file
- settings can be changed while script is running, script detect changes and reloads config
- script can not be started twice, if there is another instance of the script, the second instance will be stopped


### Requirements:
- Nerdtools
- from nerdtools install: python3-3.9.16-x86_64-1.txz, python-pip-22.2.2-x86_64-1.txz or newer
- User Scripts plugin
- Dynamix File Manager plugin is highly recommend


### Installation:
- start a terminal in unraid and copy following command to it

`git clone https://github.com/DjangoDurano/Unraid_Python_Sleep_Script && cd Unraid_Python_Sleep_Script && python3 start.py`

### Settings in .conf file:
| Command:  |  Explanation: |Possible Value/Values:   |
| ------------ | ------------ | ------------ |
|execute   |choose if script runs or not   |True / False   |
|mode   |choose mode for sleep   |shutdown / sleep   |
|excluded_days   |choose day/days that are excluded from sleep action, multiple days can be separate by ","   |monday, tuesday, wednesday, thursday, friday, saturday, sunday   |
|excluded_hours   |choose hours, only full hours, that are excluded from sleep action, multiple hours can be separate by ","    |13-14 or 13-18 or 12-13, 15-19  |
|excluded_local_ip   |exclude ip/ips for local user, for example ip from android app, multiple ips can be separate by ","   |192.168.4.20   |
|excluded_remote_ip   |exclude ip/ips for remote user, multiple ips can be separate by ","   |192.168.4.20   |
|wait_array_inactivity   |check array disks if disks are busy, if set array disks will be automatic add to "used disks", if you only want check some specific disk from array, let this option be False and add disk manually to "used_disks"   |True / False   |
|wait_disk_inactivity   |check if disks are busy, must be always True if you want check some disk   |True / False   |
|wait_user_login_inactivity   |check if remote user are logged in, local user check not possible   |True / False   |
|wait_user_login_inactivity_local   |wait for user inactivity local ,excluded ip from excluded option   |True / False|
|wait_user_login_inactivity_remote   |wait for user inactivity remote ,excluded ip from excluded option   |True / False|
|wait_network_inactivity   |check if there is some specific network traffic   |True / False   |
|wait_host_inactivity   |check for host/hosts activity   |True / False   |
|wait_smb_inactivity   |check for smb traffic   |True / False   |
|add_cache_drives   |adds automatic **all** cache drives to "used_disks"   |True / False   |
|delay_after_inactivity   |delay after all checks are have no activity to shutdown/sleep in minutes  |30   |
|ethernet_interfaces   |ethernet interface to watch for network traffic activity, multiple interfaces possible, separate by ",", if empty all interfaces will be watch (not recommend), choose your interface from "ethernet_interfaces" at config file   |eth0 or eth0, eth1   |
|network_idle_threshold   |network idle speed in kb/s for network activity   |300   |
|hosts   |host/hosts to watch for host activity, multiple hosts possible, separate by ","   |10.10.10.5 or 10.10.10.5, 192.168.5.2   |
|smb_shares   |choose shares to watch for smb activity, if empty all shares (user, disk) will be watched, choose share from "user_shares" or "disk_shares" in config file, separate by ","    |music or music, video, data   |
|wol_options_before_sleep   |wol option to be set before sleep, works only on sleep command   |p,u,m,b,g   |
|wol_interface   |interface to set wol options to   |eht0   |
|log_to|choose where to log to   |1 = logs to flash (/boot/logs/python_sleep.log), 2 = logs to syslog (/var/log/syslog), 3 = logs to flash and syslog, 4 = logs to console   |
|debug   |debugging on/off   |True / False   |
|check_for_new_disks   |check for new added disks, shares, ethernet interfaces to be added to conf file in minutes   |1440   |


| Tab:  |Explanation:   |
| ------------ | ------------ |
|[used_disk]   |all disks that will be used for monitoring disk activity, add new disk by copying disk from array/unassigned/cache disks to it, (mount_point = disk name)   |
|[unused_disk]   |list of all disks that not be used for monitoring, delete disk if you add it to "used_disks"   |
|[array_disks]   |list of all array disks   |
|[unassigned_disks]   |list of all unassigned disks   |
|[cache_disks]   |list of all cache_disks   |
|[flash_drive]   |flash_drive   |
|[user_shares]   |list of all user shares   |
|[disk_shares]   |list of all disk shares   |
|[ethernet_interfaces]   |list of all ethernet interfaces   |


| Debug option:  |Explanation:   |
| ------------ | ------------ |
|all|choose this option if all following option should be use. use carefully, better use options separately|
|smb|shows smb activity|
|network|shows network activity|
|host|shows host activity|
|sleep_timer|shows if sleep_timer is running and if sleep/shutdown is working|
|disk|shows disk activity|
|user|shows user activity|
|sys_log|shows if watchdog for local user detection is running and login/logout user|
|disk_check|shows if check for new disks/shares is running and if something is renewed|
|config|shows if config was changed|
|parity|shows if parity check is running|
|mover|shows if mover is running|
|info|shows some info about different values that are helpful for deeper debugging, (sleep timer status) |
|logger|shows if new log level/log path is set|
|process|list all multiprocess processes. use this only for deep debugging|

### Usage:
- got to flash drive into config folder and open python_sleep.conf
- set your settings from "MAIN_SETTINGS" tab
- add disks to "used_disks" if you want to watch them, pattern:
  mount_point = disk name
  sdk = WDC_1....
- best practice is to copy values from array/cache/unassigned disks to "used_disks"
- set execute to True at "MAIN_SETTINGS"
- wait for startup or go to user scripts plugin and start manually (max 10 minutes)

`Note: if option add_cache_drives or wait_array_inactivity is set, all cache/array disk will be added automatic. 
Disk name is not important it's for identification only. Mount point is absolute necessary, it  must be correct.`

### Debugging:
- set debug to True in "MAIN_SETTINGS"
- set log_to to your favorite log folder, Note: only log to flash survives a shutdown
- set debug in "DEBUG" to what your problem is. Note: it is highly recommend not to set all to True, 
this spams the log file with many mostly not needed information, set only option which maybe can cause the problem
- try `ps -ef | grep sleep.py` at terminal. this shows all processes (python3 /boot/scripts/sleep.py) from this script. 
max 6 processes are ok. normally there are 5 that the script can work correctly. the 6 process is the sleep timer process. 

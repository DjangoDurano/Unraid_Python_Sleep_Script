import re
import subprocess
import sys
from configobj import ConfigObj
import subprocess as sp
from subprocess import PIPE
from ping3 import ping
from time import sleep
from logging import Logger, ERROR
from logging.handlers import QueueHandler
from dataclasses import dataclass, field
from datetime import datetime
from os.path import getmtime, exists
from os import listdir
from pwd import getpwuid
from itertools import chain
import psutil
import multiprocessing
from multiprocessing import Manager, Value, Queue, active_children
import logging
import json


author = "Django.Durano"
version = "1.0"


def follow(_file):
    _file.seek(0, 2)
    while True:
        line = _file.readline()
        if not line:
            sleep(0.1)
            continue
        yield line


def check_array_status():
    while True:
        if sp.check_output('mdcmd status | egrep "mdState" | cut -d"=" -f2', shell=True).strip().decode("utf-8") == 'STARTED':
            break
        sleep(2)


def write_message(message, error=False):
    if error:
        with open('/boot/logs/python_error.log', "a") as file:
            file.write(f"\n{datetime.now().strftime('%b  %-d %H:%M:%S')}: {message}\n")
    else:
        with open('/var/log/syslog', "a") as file:
            file.write(f"\n{datetime.now().strftime('%b  %-d %H:%M:%S')} Python Sleep Script: {message}\n")


@dataclass
class LoggerLevel:
    smb: int = 10
    network: int = 10
    host: int = 10
    sleep_timer: int = 10
    disk: int = 10
    user: int = 10
    sys_log: int = 10
    disk_check: int = 10
    config: int = 10
    parity: int = 10
    mover: int = 10
    info: int = 10
    logger: int = 10
    process: int = 10
    error: int = 55

    def update(self, key, level):
        setattr(self, key, level)

    def update_all(self):
        for key in vars(self).keys():
            if not key == "error":
                setattr(self, key, 50)

    def set_default(self):
        for key in vars(self).keys():
            if not key == "error":
                setattr(self, key, 10)


class LoggerInit(multiprocessing.Process):
    def __init__(self, queue=None, log_file=None, error_log_file=None, sys_log=None, log_to=None):
        self.logger: Logger = logging.getLogger('python_sleep_script_multi_logger')
        self.queue = queue
        self.log_file = log_file
        self.error_log_file = error_log_file
        self.sys_log = sys_log
        self.log_to = log_to
        if self.log_file:
            self.create_logger()
        super(LoggerInit, self).__init__(name='logger')

    def run(self):
        while True:
            message = self.queue.get()
            if message is None:
                break
            self.logger.handle(message)

    def create_logger(self):

        self.logger.setLevel(50)
        self.logger.handlers.clear()
        formatter_sys = logging.Formatter('%(asctime)s Python Sleep Script: %(message)s', '%b  %-d %H:%M:%S')
        formatter = logging.Formatter('%(asctime)s: %(message)s', '%Y-%m-%d %H:%M:%S')

        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(lambda r: r.levelno == 50)
        file_handler_sys = logging.FileHandler(self.sys_log)
        file_handler_sys.setFormatter(formatter_sys)
        file_handler_sys.addFilter(lambda r: r.levelno == 50)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        error_handler = logging.FileHandler(self.error_log_file)
        error_handler.setLevel(55)
        error_handler.addFilter(lambda r: r.levelno == 55)
        self.logger.addHandler(error_handler)

        if self.log_to == 1:
            self.logger.addHandler(file_handler)
        elif self.log_to == 2:
            self.logger.addHandler(file_handler_sys)
        elif self.log_to == 3:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(file_handler_sys)
        elif self.log_to == 4:
            self.logger.addHandler(stream_handler)


class CheckTimer(multiprocessing.Process):
    def __init__(self, time=0):
        self.time = time * 60
        super(CheckTimer, self).__init__(name='check_timer')

    def run(self):
        sleep(self.time)


class SysLogWatchdog(multiprocessing.Process):
    def __init__(self, queue=None, logfile=None, login_status=None, excluded_ip=None, log_level=None):
        self.logger: Logger = logging.getLogger('syslog_watchdog')
        self.log_level: LoggerLevel = log_level
        if queue:
            self.logger.handlers.clear()
            self.logger.addHandler(QueueHandler(queue))
            self.logger.setLevel(self.log_level.sys_log)
        self.logfile = logfile
        self.login_status = login_status
        self.excluded_ip = excluded_ip
        super(SysLogWatchdog, self).__init__(name='syslog_watchdog')

    def run(self):
        self.logger.log(self.log_level.sys_log, 'Syslog watchdog started.')

        logfile = open(self.logfile, "r")
        log_lines = follow(logfile)
        for _line in log_lines:
            if "webGUI: Successful login user" in str(_line).strip():
                split_line = _line.split(" ")
                user, ip = split_line[-3], str(split_line[-1]).strip()
                if ip not in self.excluded_ip:
                    self.login_status[f'{user}_from_{ip}'] = ip
                    self.logger.log(self.log_level.sys_log, f'Login found. User {user} from {ip}.')
            if re.search("ool www\[\d*\]: Successful logout user", str(_line).strip()):
                split_line = _line.split(" ")
                user, ip = split_line[-3], str(split_line[-1]).strip()
                self.logger.log(self.log_level.sys_log, f'Logout found. User {user} from {ip}.')
                try:
                    self.login_status.pop(f'{user}_from_{ip}')
                except KeyError:
                    pass


class SleepTimer(multiprocessing.Process):
    def __init__(self, time=0, log_level=None, login_status=None, status=None,
                 mode=None, wol_settings=None, interface=None, queue=None):
        self.logger: Logger = logging.getLogger('sleep_timer')
        self.log_level: LoggerLevel = log_level
        if queue:
            self.logger.handlers.clear()
            self.logger.addHandler(QueueHandler(queue))
            self.logger.setLevel(max((self.log_level.sleep_timer, self.log_level.mover, self.log_level.parity)))
        self.time = int(time) * 60
        self.login_status = login_status
        self.status = status
        self.mode = mode
        self.wol_settings = wol_settings
        self.interface = interface
        self.poweroff_script: str = '/sbin/poweroff'
        self.powerdown_script: str = '/usr/local/sbin/powerdown'
        super(SleepTimer, self).__init__(name='sleep_timer')

    def run(self):
        sleep(self.time)
        self.logger.log(self.log_level.sleep_timer, 'Sleep is over')
        if self.mode == 'shutdown':
            if self.shutdown():
                self.logger.log(self.log_level.sleep_timer, 'Shutdown works')
                sleep(100)
        elif self.mode == 'sleep':
            if self.sleep():
                sleep(180)
                self.check_array_status()
                self.login_status.clear()
                self.status.value = False
            else:
                self.status.value = False

    @staticmethod
    def check_array_status():
        while True:
            if sp.check_output('mdcmd status | egrep "mdState" | cut -d"=" -f2', shell=True).strip().decode("utf-8") == 'STARTED':
                break
            sleep(2)

    def check_if_mover_runs(self):
        if sp.check_output('/usr/local/sbin/mover status | egrep "mover" | cut -d":" -f2', shell=True).strip().decode("utf-8") == 'running':
            self.logger.log(self.log_level.mover, 'Mover is running.')
            return True
        return False

    def check_if_parity_check_runs(self):
        if not sp.check_output('mdcmd status | egrep -w "mdResync" | cut -d"=" -f2', shell=True).strip().decode("utf-8") == '0':
            self.logger.log(self.log_level.parity, 'Parity check is running.')

    def shutdown(self):
        _script = None
        if not self.check_if_mover_runs() and not self.check_if_parity_check_runs():
            if exists(self.poweroff_script):
                _script = self.poweroff_script
            elif exists(self.powerdown_script):
                _script = self.powerdown_script
            else:
                self.logger.log(self.log_level.error, 'No powerdown script present!')
                return False

            sp.call(_script)
            self.status.value = True
            return True
        return False

    def sleep(self):
        if not self.check_if_mover_runs() and not self.check_if_parity_check_runs():
            self.status.value = True
            sleep(10)
            if self.wol_settings:
                self.pre_sleep_activity()
            self.logger.log(self.log_level.sleep_timer, 'sleep works')
            process = sp.Popen('echo -n mem >/sys/power/state', shell=True, stdout=PIPE, stderr=PIPE)
            process.wait()
            output, error = process.communicate()

            if error:
                self.logger.log(self.log_level.error, f'Sleep not work: {error}')
                return False
            return True
        return False

    def pre_sleep_activity(self):
        process = sp.Popen(['ethtool', '-s', self.interface, 'wol', self.wol_settings], stdout=PIPE, stderr=PIPE)
        output, err = process.communicate()

        if err:
            self.logger.log(self.log_level.sleep_timer, f'Following error appears at setting wol options: {err}')
        else:
            self.logger.log(self.log_level.sleep_timer, f'Set the wol options: {output}')


@dataclass
class SleepScript:
    log_file: str = '/boot/logs/python_sleep.log'
    sys_log: str = '/var/log/syslog'
    error_log: str = '/boot/logs/python_error.log'
    config_path: str = '/boot/config/python_sleep.conf'
    disks_config: str = '/var/local/emhttp/disks.ini'
    user_shares_path: str = '/mnt/user'
    disk_shares_path: str = '/mnt/disks'
    unassigned_disks_config: str = '/var/local/emhttp/unassigned.devices.ini'
    logger: Logger = logging.getLogger('python_sleep_script')
    config: ConfigObj = None
    check_timer: CheckTimer = CheckTimer()
    sleep_timer: SleepTimer = SleepTimer()
    multi_logger: LoggerInit = LoggerInit()
    queue: Queue = None
    sys_log_watchdog: SysLogWatchdog = SysLogWatchdog()
    ethernet_interfaces: list = field(default_factory=list)
    excluded_days: list = field(default_factory=list)
    excluded_hours: list = field(default_factory=list)
    excluded_local_ip: list = field(default_factory=list)
    excluded_remote_ip: list = field(default_factory=list)
    hosts: list = field(default_factory=list)
    user_shares: list = field(default_factory=list)
    disk_shares: list = field(default_factory=list)
    smb_shares: list = field(default_factory=list)
    mode: str = None
    login_status: any = None
    manager: Manager = None
    wol_option: str = None
    wol_interface: str = None
    config_mtime: float = 0
    bytes_sent_before: float = 0
    bytes_recv_before: float = 0
    network_idle_threshold: int = 100
    delay_after_inactivity: int = 30
    log_level: LoggerLevel = LoggerLevel()
    ongoing: bool = True
    disk_check: bool = False
    time: datetime = datetime.now()
    status: Value = Value('i', False)
    first_start: bool = True
    last_config_check: int = datetime.now().strftime('%H')
    last_config_check_counter: int = 0

    def __post_init__(self):
        self.check_if_script_always_runs()
        write_message('Sleep script execution started.')
        self.config = ConfigObj(self.config_path)
        self.queue = Queue()
        self.logger.addHandler(QueueHandler(self.queue))
        self.logger.setLevel(50)
        self.set_log_level()
        self.get_server_info()
        self.start_logger()

        if self.disk_check:
            self.config.write()
            self.logger.log(self.log_level.config, 'Config written.')

        if not self.config.get('MAIN_SETTINGS').as_bool('execute'):
            self.queue.put(None)
            sys.exit('Sleep script execution stopped. Execute is set to False at config.')

        self.manager = Manager()
        self.login_status = self.manager.dict()
        self.set_settings()

        self.config_mtime = getmtime(self.config_path)

    def check(self):
        self.logger.log(self.log_level.process, active_children())
        self.logger.log(self.log_level.info, f'Sleep timer status: {bool(self.status.value)}')

        if bool(self.status.value) and self.mode == 'shutdown':
            sleep(5)
            sys.exit('Sleep timer over. System shutdown.')
        elif bool(self.status.value) and self.mode == 'sleep':
            while True:
                if not bool(self.status.value):
                    break
                sleep(5)
        elif not bool(self.status.value):
            self.ongoing = False

            if not getmtime(self.config_path) == self.config_mtime and not self.first_start:
                if self.config_check():
                    self.config.reload()
                    self.disk_check = False
                    if not self.config.get('MAIN_SETTINGS').as_bool('execute'):
                        self.queue.put(None)
                        sys.exit('Sleep script execution stopped. Execute is set to False at config.')
                    if self.config.get('MAIN_SETTINGS').as_bool('wait_array_inactivity'):
                        self.add_array_disks_to_used()
                    else:
                        self.clear_used_disks()
                    self.clear_unused_disks()
                    self.set_settings()
                    self.logger.log(self.log_level.config, 'Config reloaded.')
                    if self.disk_check:
                        self.config.write()
                        self.logger.log(self.log_level.config, 'Config written.')
                    self.config_mtime = getmtime(self.config_path)

            if not self.check_timer.is_alive() and self.config.get('MAIN_SETTINGS').as_int('check_for_new_disks') > 0:
                self.disk_check = False
                self.get_server_info()
                self.start_check_timer()
                self.logger.log(self.log_level.disk_check, 'Check for new disks.')
                if self.disk_check:
                    self.config.write()
                    self.logger.log(self.log_level.disk_check, 'Config written.')

            if self.config.get('MAIN_SETTINGS').as_bool('wait_disk_inactivity'):
                self.check_hdd_activity()
            if self.config.get('MAIN_SETTINGS').as_bool('wait_network_inactivity'):
                self.check_ethernet_activity()
            if self.config.get('MAIN_SETTINGS').as_bool('wait_host_inactivity'):
                self.check_ip()
            if self.config.get('MAIN_SETTINGS').as_bool('wait_user_login_inactivity'):
                self.check_users()
            if self.config.get('MAIN_SETTINGS').as_bool('wait_smb_inactivity'):
                self.check_smb_status()

            if self.first_start:
                self.first_start = False

            if not datetime.now().strftime('%A') in self.excluded_days or not datetime.now().strftime('%H') in self.excluded_hours:
                if self.ongoing and self.sleep_timer.is_alive():
                    self.sleep_timer.terminate()
                    self.logger.log(self.log_level.sleep_timer, 'Sleep timer exited.')
                elif not self.ongoing and not self.sleep_timer.is_alive() and not bool(self.status.value):
                    self.start_sleep_timer()
                    self.logger.log(self.log_level.sleep_timer, 'Sleep timer started.')

    def set_settings(self):
        self.login_status.clear()
        self.excluded_local_ip = self.manager.list()
        self.hosts = self.config.get('MAIN_SETTINGS').as_list('hosts')
        self.smb_shares = self.config.get('MAIN_SETTINGS').as_list('smb_shares') if self.config['MAIN_SETTINGS']['smb_shares'] else []
        self.wol_option = self.config['MAIN_SETTINGS']['wol_options_before_sleep'] if self.config['MAIN_SETTINGS']['wol_options_before_sleep'] else None
        self.wol_interface = self.config['MAIN_SETTINGS']['wol_interface']
        self.mode = self.config['MAIN_SETTINGS']['mode']
        self.network_idle_threshold = self.config.get('MAIN_SETTINGS').as_int('network_idle_threshold')
        self.delay_after_inactivity = self.config.get('MAIN_SETTINGS').as_int('delay_after_inactivity')
        self.excluded_days.extend(self.config.get('MAIN_SETTINGS').as_list('excluded_days'))
        self.excluded_remote_ip.extend(self.config.get('MAIN_SETTINGS').as_list('excluded_remote_ip')
                                       if self.config['MAIN_SETTINGS']['excluded_remote_ip'] else [])
        self.excluded_local_ip.extend(self.config.get('MAIN_SETTINGS').as_list('excluded_local_ip')
                                      if self.config['MAIN_SETTINGS']['excluded_local_ip'] else [])
        self.status = Value('i', False)
        self.get_hours()

        if not self.first_start:
            if self.multi_logger.is_alive():
                self.queue.put(None)
                self.multi_logger.join()
            self.set_log_level()
            self.start_logger()

        if self.config.get('MAIN_SETTINGS').as_bool('wait_network_inactivity'):
            self.set_interfaces_to_watch()
            self.bytes_sent_before, self.bytes_recv_before = self.get_bytes()
            self.time = datetime.now()

        if self.sleep_timer.is_alive():
            self.sleep_timer.terminate()

        if self.check_timer.is_alive() and self.config.get('MAIN_SETTINGS').as_int('check_for_new_disks') > 0:
            self.check_timer.terminate()
            self.start_check_timer()
        elif self.config.get('MAIN_SETTINGS').as_int('check_for_new_disks') > 0:
            self.start_check_timer()

        if self.sys_log_watchdog.is_alive():
            self.sys_log_watchdog.terminate()
            self.start_syslog_watchdog()
        else:
            self.start_syslog_watchdog()

    def start_syslog_watchdog(self):
        self.sys_log_watchdog = SysLogWatchdog(queue=self.queue, log_level=self.log_level, logfile=self.sys_log,
                                               login_status=self.login_status, excluded_ip=self.excluded_local_ip)
        self.sys_log_watchdog.start()

    def start_logger(self):
        self.multi_logger = LoggerInit(queue=self.queue, log_file=self.log_file, error_log_file=self.error_log,
                                       sys_log=self.sys_log, log_to=self.config.get('MAIN_SETTINGS').as_int('log_to'))
        self.multi_logger.start()

    def start_check_timer(self):
        self.check_timer = CheckTimer(time=self.config.get('MAIN_SETTINGS').as_int('check_for_new_disks'))
        self.check_timer.start()

    def start_sleep_timer(self):
        self.sleep_timer = SleepTimer(time=self.delay_after_inactivity, login_status=self.login_status,
                                      wol_settings=self.wol_option, interface=self.wol_interface,
                                      mode=self.mode, status=self.status, log_level=self.log_level,
                                      queue=self.queue)
        self.sleep_timer.start()

    def set_interfaces_to_watch(self):
        self.ethernet_interfaces.clear()
        self.ethernet_interfaces.extend(self.config.get('MAIN_SETTINGS').as_list('ethernet_interfaces')
                                        if self.config['MAIN_SETTINGS']['ethernet_interfaces'] else [])
        if not self.ethernet_interfaces:
            self.ethernet_interfaces = [interface for interface in self.config['ethernet_interfaces'].keys()]

    def set_log_level(self):
        if self.config.get('MAIN_SETTINGS').as_bool('debug'):
            if self.config.get('DEBUG').as_bool('all'):
                self.log_level.update_all()
            else:
                for key in self.config['DEBUG']:
                    if self.config.get('DEBUG').as_bool(key) and not key == 'all':
                        self.log_level.update(key=key, level=50)
                    elif not self.config.get('DEBUG').as_bool(key) and not key == 'all':
                        self.log_level.update(key=key, level=10)
        else:
            self.log_level.set_default()

        self.logger.log(self.log_level.logger, 'New log level set.')

    def get_server_info(self):
        if self.get_ethernet_interfaces():
            self.logger.log(self.log_level.disk_check, 'Nics renewed.')
        if self.get_drives():
            self.logger.log(self.log_level.disk_check, 'Drives renewed.')
        if self.get_user_shares():
            self.logger.log(self.log_level.disk_check, 'User shares renewed.')
        if self.get_disk_shares():
            self.logger.log(self.log_level.disk_check, 'Disk shares renewed.')

    def get_hours(self):
        excluded_hours = self.config.get('MAIN_SETTINGS').as_list('excluded_hours') if self.config['MAIN_SETTINGS'][
            'excluded_hours'] else []
        self.excluded_hours.clear()

        for hour in excluded_hours:
            h1, h2 = hour.split("-")
            h2 = 0 if int(h2) == 24 else int(h2)
            h = int(h1)
            while True:
                h += 1
                h = h if not h == 24 else 0
                if int(h) == int(h2):
                    break
                else:
                    self.excluded_hours.append(str(h))

            if h1 not in self.excluded_hours:
                self.excluded_hours.append(h1)
            if h2 not in self.excluded_hours:
                self.excluded_hours.append(h2)

    def get_bytes(self):
        bytes_sent = 0
        bytes_recv = 0

        eth_interfaces = {nic: data for nic, data in psutil.net_io_counters(pernic=True).items() if
                          nic in self.ethernet_interfaces}

        for interface in eth_interfaces:
            bytes_sent += eth_interfaces[interface].bytes_sent
            bytes_recv += eth_interfaces[interface].bytes_recv

        return bytes_sent, bytes_recv

    def check_ethernet_activity(self):

        sleep(1)
        time_delta = round((datetime.now() - self.time).total_seconds())

        bytes_sent_after, bytes_recv_after = self.get_bytes()
        us, ds = bytes_sent_after - self.bytes_sent_before, bytes_recv_after - self.bytes_recv_before

        upload_speed = us / time_delta
        download_speed = ds / time_delta

        act_speed = round((upload_speed + download_speed) / 1024)

        self.bytes_sent_before = bytes_sent_after
        self.bytes_recv_before = bytes_recv_after
        self.time = datetime.now()

        if act_speed > self.config.get('MAIN_SETTINGS').as_int('network_idle_threshold'):
            self.ongoing = True
            self.logger.log(self.log_level.network, f'Network activity is ongoing.'
                            f'\nDownload Speed: {self.get_size(download_speed)}/s | Upload Speed: {self.get_size(upload_speed)}/s')

    def check_ip(self):
        for ip in self.config.get('MAIN_SETTINGS').as_list('hosts'):
            if ping(ip):
                self.ongoing = True
                self.logger.log(self.log_level.host, f'Host activity from {ip}.')

    def check_users(self):
        users = psutil.users()

        if self.config.get('MAIN_SETTINGS').as_bool('wait_user_login_inactivity_remote'):
            if users:
                for user in users:
                    if user.host not in self.excluded_remote_ip:
                        self.ongoing = True
                        self.logger.log(self.log_level.user,
                                        f'User activity: {user.name} from terminal ({user.terminal}) host ({user.host})')

        if self.config.get('MAIN_SETTINGS').as_bool('wait_user_login_inactivity_local'):
            if self.login_status:
                self.ongoing = True
                self.logger.log(self.log_level.user, f'Local user activity from: {list(self.login_status.keys())}.')

    def check_hdd_activity(self):
        disks: list = [disk for disk in self.config['used_disks'].keys()]

        disks_old = {disk: {'write_merged_count': data.write_merged_count, 'read_merged_count': data.read_merged_count}
                     for disk, data in psutil.disk_io_counters(perdisk=True, nowrap=True).items() if disk in disks}
        sleep(3)
        disks_new = {disk: {'write_merged_count': data.write_merged_count, 'read_merged_count': data.read_merged_count}
                     for disk, data in psutil.disk_io_counters(perdisk=True, nowrap=True).items() if disk in disks}

        for disk in disks_old.keys():
            if not disks_old[disk] == disks_new[disk]:
                self.logger.log(self.log_level.disk, f'Disk activity ongoing from disk: {disk}')
                self.ongoing = True

    def check_smb_status(self):
        try:
            process = sp.Popen(['smbstatus', '-L', '-j'], stdout=PIPE, stderr=PIPE)
            output, err = process.communicate()

            if err:
                self.logger.log(self.log_level.error, err)
            else:
                smb_status = json.loads(output)

                for open_file in smb_status['open_files'].keys():
                    for key in smb_status['open_files'][open_file]['opens'].keys():
                        if smb_status['open_files'][open_file]['opens'][key]['oplock']:
                            try:
                                _, share_type, share_name = smb_status['open_files'][open_file]['service_path'][1:].split("/")
                            except ValueError:
                                share_type = None
                                share_name = f"{smb_status['open_files'][open_file]['service_path']}/{smb_status['open_files'][open_file]['filename']}"
                            filename = smb_status['open_files'][open_file]['filename'].split("/")[-1]
                            if self.smb_shares:
                                if share_name in self.smb_shares:
                                    self.ongoing = True
                                    self.logger.log(self.log_level.smb, f"Ongoing smb traffic:\n"
                                                    f"User: {getpwuid(smb_status['open_files'][open_file]['opens'][key]['uid']).pw_name} | "
                                                    f"Share: {share_name} | Share Type: {share_type} | File: {filename}")
                            else:
                                self.ongoing = True
                                self.logger.log(self.log_level.smb, f"Ongoing smb traffic:\n"
                                                f"User: {getpwuid(smb_status['open_files'][open_file]['opens'][key]['uid']).pw_name} | "
                                                f"Share: {share_name} | Share Type: {share_type} | File: {filename}")
                            break

        except subprocess.CalledProcessError as error:
            self.logger.log(self.log_level.error, error)

    def get_ethernet_interfaces(self):
        interfaces = [interface for interface in psutil.net_if_stats().keys() if 'veth' not in interface]

        if not sorted(interfaces) == sorted(list(self.config['ethernet_interfaces'].keys())):
            self.config['ethernet_interfaces'] = {}
            for interface in interfaces:
                self.config['ethernet_interfaces'][interface] = interface

            self.disk_check = True
            return True
        return False

    def get_user_shares(self):

        self.user_shares = listdir(self.user_shares_path)

        if not self.user_shares == list(self.config['user_shares'].keys()):
            self.config['user_shares'] = {}
            self.disk_check = True
            for share in self.user_shares:
                self.config['user_shares'][share] = share

            return True
        return False

    def get_disk_shares(self):

        self.disk_shares = listdir(self.disk_shares_path)

        if not self.disk_shares == list(self.config['disk_shares'].keys()):
            self.config['disk_shares'] = {}
            self.disk_check = True
            for share in self.disk_shares:
                self.config['disk_shares'][share] = share

            return True
        return False

    def get_drives(self):
        config_disks = ConfigObj(self.disks_config)
        config_unassigned_disk = ConfigObj(self.unassigned_disks_config)
        drives: dict = {}

        process = sp.Popen('ls -l /dev/disk/by-id/[asun]*', shell=True, stdout=PIPE, stderr=PIPE)
        output, err = process.communicate()

        if err:
            self.logger.log(self.log_level.error, f'An error appears from command (ls -l /dev/disk/by-id/[asun]*):\n{err}')
        else:
            for line in output.splitlines():
                for x in str(line).split(" "):
                    if re.findall(r"nvme-[A-Z]|ata-[A-Z]|ide-[A-Z]|scsi-[A-Z]|usb-[A-Z]", x) and "part" not in x:
                        drives[self.__get_drive_mount_point(line)] = self.__get_drive_name(x)

            for section in config_disks.sections:
                if config_disks[section]['device']:
                    if not self.check_if_disk_exists(mount=config_disks[section]['device'],
                                                     disk=drives[config_disks[section]['device']]):
                        if config_disks[section]['type'] == 'Data':
                            self.add_disks(check='array', _type='array_disks',
                                           mount=config_disks[section]['device'],
                                           disk=drives[config_disks[section]['device']])
                        if config_disks[section]['type'] == 'Parity':
                            self.add_disks(check='array', _type='array_disks',
                                           mount=config_disks[section]['device'],
                                           disk=drives[config_disks[section]['device']])
                        if config_disks[section]['type'] == 'Cache':
                            self.add_disks(check='cache', _type='cache_disks',
                                           mount=config_disks[section]['device'],
                                           disk=drives[config_disks[section]['device']])
                        if config_disks[section]['type'] == 'Flash':
                            self.add_disks(check='flash', _type='flash_drive', mount=config_disks[section]['device'],
                                           disk=drives[config_disks[section]['device']])

            for section in config_unassigned_disk.sections:
                if not config_unassigned_disk[section]['DEVTYPE'] == "partition":
                    if self.__get_drive_name(section) in drives.keys():
                        if not self.check_if_disk_exists(mount=self.__get_drive_name(section),
                                                         disk=drives[self.__get_drive_name(section)]):
                            self.add_disks(_type='unassigned_disks',
                                           mount=self.__get_drive_name(section),
                                           disk=drives[self.__get_drive_name(section)])

        self.clear_unused_disks()
        self.clear_used_disks()

        if self.disk_check:
            return True
        return False

    def add_disks(self, _type, mount, disk, check: str = None):
        try:
            _ = self.config[_type][mount]
            if not _type == 'flash_drive':
                _ = self.config['unused_disks'][mount]
            if self.config.get('MAIN_SETTINGS').as_bool('wait_array_inactivity') and _type == 'array_disks':
                _ = self.config['used_disks'][mount]
            if self.config.get('MAIN_SETTINGS').as_bool('add_cache_drives') and _type == 'cache_disks':
                _ = self.config['used_disks'][mount]
            if not self.config[_type][mount] == disk:
                self.used_check(check=check, mount=mount, disk=disk, _type=_type)
                self.disk_check = True
        except KeyError:
            self.used_check(check=check, mount=mount, disk=disk, _type=_type)
            self.disk_check = True

    def used_check(self, mount, disk, check, _type):
        if check == 'array':
            if self.config.get('MAIN_SETTINGS').as_bool('wait_array_inactivity'):
                self.config['used_disks'][mount] = disk
                self.config[_type][mount] = disk
            else:
                self.config['unused_disks'][mount] = disk
                self.config[_type][mount] = disk
        elif check == 'cache':
            if self.config.get('MAIN_SETTINGS').as_bool('add_cache_drives'):
                self.config['used_disks'][mount] = disk
                self.config[_type][mount] = disk
            else:
                self.config['unused_disks'][mount] = disk
                self.config[_type][mount] = disk
        elif check == 'flash':
            self.config[_type][mount] = disk
        else:
            self.config['unused_disks'][mount] = disk
            self.config[_type][mount] = disk

    def clear_used_disks(self):
        for mount, disk in self.config['used_disks'].items():
            if not self.config.get('MAIN_SETTINGS').as_bool('wait_array_inactivity') and mount in self.config['array_disks'].keys():
                self.config['used_disks'].pop(mount)
                self.disk_check = True

    def clear_unused_disks(self):
        drives: list = []
        for disk in chain(self.config['array_disks'].keys(), self.config['unassigned_disks'].keys(), self.config['cache_disks'].keys()):
            if disk not in self.config['used_disks'].keys():
                drives.append(disk)

        drives_dict: dict = {**self.config['array_disks'], **self.config['unassigned_disks'], **self.config['cache_disks']}

        if not list(self.config['unused_disks'].keys()) == drives:
            self.config['unused_disks'] = {}
            for mount, disk in drives_dict.items():
                if mount not in self.config['used_disks'].keys() or not disk == self.config['used_disks'][mount]:
                    self.config['unused_disks'][mount] = disk
                    self.disk_check = True

    def add_array_disks_to_used(self):
        for mount, disk in self.config['array_disks'].items():
            try:
                _ = self.config['used_disks'][mount]
            except KeyError:
                self.config['used_disks'][mount] = disk
                self.disk_check = True

    def check_if_disk_exists(self, mount, disk):
        drives: dict = {**self.config['array_disks'], **self.config['unassigned_disks'],
                        **self.config['cache_disks'], **self.config['flash_drive']}

        if mount in drives.keys() and drives[mount] == disk:
            return True
        return False

    def config_check(self):
        # check if config was reloaded more than 20 times within last hour
        if not self.last_config_check_counter > 20:
            if self.last_config_check == datetime.now().strftime('%H'):
                self.last_config_check_counter += 1
            else:
                self.last_config_check_counter = 0
                self.last_config_check = datetime.now().strftime('%H')
            return True

        self.logger.log(self.log_level.config, 'Config reloaded more than 20 times within the last hour. Check Script.')
        return False

    @staticmethod
    def __get_drive_name(name: str):
        return name.split("/")[-1].split("-", maxsplit=1)[-1]

    @staticmethod
    def __get_drive_mount_point(mount: str):
        return str(mount).split(" ")[-1].split("/")[-1].split("-")[-1].replace("'", "")

    @staticmethod
    def get_size(_bytes):
        for unit in ['', 'K', 'M', 'G', 'T', 'P']:
            if _bytes < 1024:
                return f"{_bytes:.2f} {unit}B"
            _bytes /= 1024

    @staticmethod
    def check_if_script_always_runs():
        pids: list = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == "python3" and "sleep.py" in proc.info['cmdline'][1]:
                    pids.append(proc.info['pid'])
            except IndexError:
                continue

        if len(pids) > 1:
            sys.exit('Sleep script execution stopped. Another instance is running.')


if __name__ == '__main__':
    check_array_status()
    script: SleepScript = None

    try:
        script = SleepScript()
        while True:
            script.check()
            sleep(1)
    except KeyboardInterrupt:
        write_message('Sleep script execution stopped by user.')
    except SystemExit as e:
        write_message(e)
    finally:
        try:
            if script.config.get('MAIN_SETTINGS').as_bool('execute'):
                if script.check_timer.is_alive():
                    script.check_timer.terminate()
                if script.sleep_timer.is_alive():
                    script.sleep_timer.terminate()
                if script.sys_log_watchdog.is_alive():
                    script.sys_log_watchdog.terminate()
                if script.multi_logger.is_alive():
                    script.queue.put(None)
        except AttributeError:
            pass

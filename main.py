import subprocess
import time
import syslog
from simple_pid import PID

# USE AT YOUR OWN RISK
# PID fan control for motherboard with IPMI only (and Linux, tested with ubuntu server 20.04)
# for motherboards other than ASRockRack E3C246D4U will NEED modification for location of fan headers
# uses ipmi fan header mappings for a with HDD regulating fans connected to REAR_FAN_2 and FRONT_FAN_2
# required module simple-pid see here: https://github.com/m-lundberg/simple-pid
# also requires smart-tools (smartctl) and ipmitool


def get_list_hdd():  # returns a list of hd* or sd* for which to monitor temp
    drive_list_string = (subprocess.check_output("lsblk --nodeps -n -o name | grep [sd*\|hd*]", shell=True)).decode(
        "utf-8")
    drive_list = drive_list_string.splitlines()  # parse list of drive on '/n'
    return drive_list


def getMaxTemp():
    hdd_temp = []
    drives = get_list_hdd()

    # getting temp for each drive in drives list then parsing with grep to get the temp line and then awk to get value field
    for drive in drives:  # awk '{print $10}' may need to be modified for your system if this field doesn't return temp
        hdd_temp.append(
            int(subprocess.check_output("smartctl -a /dev/" + drive + " | grep Temperature_Celsius | awk '{print $10}'",
                                        shell=True)))

    return max(hdd_temp)  # using max reported hdd temp


def set_fan_speed(fanspeed):
    # control fan temps
    # ipmitool raw 0x3a 0x01 0x00 0x00 REAR_FAN1 REAR_FAN2 FRONT_FAN1 FRONT_FAN2 0x00 0x00

    rear_fan_2 = fanspeed
    front_fan_2 = fanspeed
    subprocess.check_output(f"ipmitool raw 0x3a 0x01 0x00 0x00 0x12 {fanspeed} 0x20 {fanspeed} 0x00 0x00",
                            shell=True)


def print_fan_settings():
    # get current fan settings
    fan_settings = str(subprocess.check_output("ipmitool raw 0x3a 0x02", shell=True))
    fan_settings_list = (fan_settings.strip()).split()

    # remove unecessary text
    del fan_settings_list[0]
    del fan_settings_list[7]

    syslog.syslog("fancontrol settings: " + str(fan_settings_list) + " temp: " + str(getMaxTemp()))


def main():
    # Define system temps where fans will be active
    MAX_HD_TEMP = 35
    SAMPLE_TIME = 60 * 5  # 300 seconds or 5 minutes

    pid = PID(-1, -0.1, -0.05, setpoint=MAX_HD_TEMP)  # 35 C HD temperature
    pid.sample_time = SAMPLE_TIME
    pid.output_limits = (4, 100) #Asrock uses 0x04 to 0x64 steps to regulate, SUPERMICRO may use 0x04 to 0xFF

    # enable PID temperature regulation using max hd temp and simple_pid
    # pid object will return values to keep max hdd temp around MAX_HD_TEMP
    while True:
        control = pid(getMaxTemp())  # feeds current measured hdd max temp to the pid object
        set_fan_speed(int(control))  # then use the control value returned to set new fan speeds
        print_fan_settings()
        time.sleep(SAMPLE_TIME)


if __name__ == '__main__':
    main()

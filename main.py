import subprocess
import time
import syslog
from simple_pid import PID

# USE AT YOUR OWN RISK
# PID fan control for motherboard with IPMI only (and Linux, tested with ubuntu server 20.04)
# for motherboards other than ASRockRack E3C246D4U will NEED modification for location of fan headers
# uses ipmi fan header mappings for a with HDD regulating fans connected to REAR_FAN_2 and FRONT_FAN_2
# required module simple-pid see here: https://github.com/m-lundberg/simple-pid
# also requires smartmon-tools (smartctl) and ipmitool


MAX_HD_TEMP = 35  # Regulate fans to keep measured HD temp at MAX_HD_TEMP
SAMPLE_TIME = 60 * 5  # 300 seconds or 5 minute sample time
DRIVE_LIST = ['sda', 'sdb', 'sdc', 'sdd', 'sde']  # drives for which hdd temp will be probed at interval SAMPLE_TIME


def getMaxTemp():
    hdd_temp = []

    # getting temp for each drive in drives list then parsing with grep to get the temp line and then awk to get value field
    for drive in DRIVE_LIST:  # awk '{print $10}' may need to be modified for your system if this field doesn't return temp
        temp = subprocess.check_output("smartctl -a /dev/" + drive + " | grep Temperature_Celsius | awk '{print $10}'",
                                        shell=True)
        temp = int(temp.strip().decode('utf-8'))
        hdd_temp.append(temp)

    return max(hdd_temp)  # using max reported hdd temp


def set_fan_speed(fanspeed):
    # ipmitool raw 0x3a 0x01 0x00 0x00 REAR_FAN1 REAR_FAN2 FRONT_FAN1 FRONT_FAN2 0x00 0x00
    # mapping for asrock E3C246D4U with cooling fans on REAR_FAN2, FRONT_FAN2

    # add dual zone later
    #rear_fan_2 = fanspeed
    #front_fan_2 = fanspeed
    subprocess.check_output(f"ipmitool raw 0x3a 0x01 0x00 0x00 0x12 {fanspeed} 0x20 {fanspeed} 0x00 0x00",
                            shell=True)


def print_fan_settings(settings):
    syslog.syslog("fancontrol setting: " + str(settings) + " temp: " + str(getMaxTemp()))


def main():
    pid = PID(-2, -0.05, -0.5, setpoint=MAX_HD_TEMP)  # tries to converge on MAX_HD_TEMP temperature
    # tuning params are negative as increase in input to set_fan_speed lowers temps
    pid.sample_time = SAMPLE_TIME
    pid.output_limits = (4, 100)  # Asrock uses 0x04 to 0x64 steps to regulate, SUPERMICRO may use 0x04 to 0xFF

    # enable PID temperature regulation using max hd temp and simple_pid
    # pid object will return values to keep max hdd temp around MAX_HD_TEMP
    while True:
        control = pid(getMaxTemp())  # feeds current measured hdd max temp to the pid object
        set_fan_speed(int(control))  # then use the control value returned to set new fan speeds
        print_fan_settings(control)
        time.sleep(SAMPLE_TIME)


if __name__ == '__main__':
    main()

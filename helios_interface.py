import numpy as np

import astropy.coordinates as coord
from astropy.time import Time
import astropy.units as u

import time
import telnetlib
import datetime

def get_sun_position(loc, t):
    t = Time(t, format='isot')
    loc = coord.EarthLocation(lon=loc[0] * u.deg,
                                         lat=loc[1] * u.deg)
    altaz = coord.AltAz(location=loc, obstime=t)
    sun = coord.get_sun(t)

    alt = sun.transform_to(altaz).alt.deg
    az = sun.transform_to(altaz).az.deg
    return az, alt

HELIOS_FLOAT_EDITABLE_CFG = {
 "ALT_ENCODER_ZERO": "alte0",
 "ALT_KP": "alt_kp",
 "ALT_MIN_E": "alt_me",
 "AZI_ENCODER_ZERO": "azie0",
 "AZI_KP": "azi_kp",
 "AZI_MIN_E": "azi_me",
 "GEO_LAT": "lat",
 "GEO_LON": "lon",
 "AZI_MAX_SPEED_VALUE":  "azi_Msv",
 "AZI_VOLT_TO_DEG": "aziv2d",
 "ALT_MAX_SPEED_VALUE": "alt_Msv",
 "ALT_VOLT_TO_DEG": "aziv2d",
 "SPEED_TO_PWM_ALT": "alt_s2p",
 "SPEED_TO_PWM_AZI": "azi_s2p",
 "SLEEP_ALT": "altnap",
 "SLEEP_AZI": "azinap",
 "ALT_SCENE_ACCEL": "alt_sca",
 "AZI_SCENE_ACCEL": "azi_sca",
 "MIN_BATTERY_LEVEL": "minbl"}

HELIOS_INT_EDITABLE_CFG = {"ENCODER_OVERSAMPLING": 'overs',
                            "LAST_NETWORK":'lastnet',
                            "PWM_MIN_ALT": 'alt_mPWM',
                            "PWM_MIN_AZI": 'azi_mPWM',
                            "LOG_LEVEL": 'logl',
                            "LOG_DELETE_AFTER_DAYS": 'logr'}

HELIOS_INT_COMPTIME_CFG = ["MAX_BLIND_MOVE_TIME_MS",
"MAX_DAILY_TASKS",
"MAX_LOG_FILES",
"MAX_SCENES",
"MAX_SCENES_IN_SEQUENCE",
"MAX_SLEEP_S",
"MAX_WIFI_NETWORKS",
"N_WIFI_ATTEMPTS",
"SAFETY_MAX_YEAR",
"SAFETY_MIN_YEAR",
"SAFETY_TIME_BEFORE_FIRST_SCENE",
"SAFETY_TIME_BEFORE_SEQUENCE",
"SCENE_LEN",
"SCENE_LEN_SECONDS",
"SCHEDULE_TIME_DELTA",
"SLEEP_TIME_S",
"TELNET_WATCHDOG_TIME",
"WAKEUP_TIME_BEFORE_SCHEDULE_S",
"WIFI_WATCHDOG_TIME",
"PWM_MAX_VALUE",
"SCENE_DT"]

HELIOS_FLOAT_COMPTIME_CFG = [
"ATM_PRESSURE",
"ATM_TEMPERATURE",
"BATTERY_MAX_mV",
"BATTERY_MIN_mV",
"BATTERY_R1_kOHM",
"BATTERY_R2_kOHM",
"BATTERY_VOLTAGE_DIVIDER_FAC",
"MIN_ALLOWED_SPEED",
"WATCHDOG_TIME_FACTOR"]

class HeliosSchedule:
    def __init__(self, sch_id, timestr, sch_type, sequence=[], y=None, m=None, d=None):
        self.time = datetime.datetime.strptime(timestr,"%H:%M:%S").time()
        self.type = sch_type
        self.id = sch_id
        self.year = y
        self.month = m
        self.day = d

        assert self.type in ['wifi', 'sequence']
        if self.type == 'sequence':
            self.sequence = sequence
        else:
            self.sequence = []

    def __eq__(self, other):
        return self.time == other.time
    def __gt__(self, other):
        return self.time > other.time
    def __lt__(self, other):
        return self.time < other.time
    def __ge__(self, other):
        return self.time >= other.time
    def __le__(self, other):
        return self.time <= other.time
    def __str__(self):
        tz_delta = datetime.datetime.now(datetime.timezone.utc).astimezone().utcoffset()
        local_time = (datetime.datetime.fromisoformat('1900-01-01 '+str(self.time))+tz_delta).time()
        if self.type == 'wifi':
            s = "{:d} - {:s} wifi".format(self.id, str(local_time))
        else:
            s = "{:d} - {:s} sequence".format(self.id, str(local_time))
            for scene in self.sequence:
                s += ' {:s}'.format(scene)
        if self.year is not None and self.day is not None and self.month is not None:
            s += ' [{:04d}/{:02d}/{:02d}]'.format(self.year, self.day, self.month)
        return s

class HeliosUnit:
    def __init__(self, ip_addr, nickname=None):
        self.ip_addr = ip_addr

        self.connect()

        self.id = self.get_id()
        if nickname is None:
            self.nickname = self.id
        else:
            self.nickname = nickname

        self.alt = np.nan
        self.azi = np.nan

        self.lat = np.nan
        self.lon = np.nan

        self.sequence_max = 120
        self.sequence_dt = 0.5

        self.cfg = {}

        self.get_geo()
        self.get_cfg()
        self.get_position()
        self.get_list_scene()
        self.get_wifi_conn()
        self.get_schedule()

        self.alt_setpoint = self.alt
        self.azi_setpoint = self.azi

        #assert self.check_sun_position()
        assert self.check_device_clock()

    def __del__(self):
        self.disconnect()

    def reboot(self):
        self.cmd_get_answare("reboot", 0)
        time.sleep(10)

    def connect(self):
        try:
            self.tn = telnetlib.Telnet(self.ip_addr, timeout=10)
        except TimeoutError:
            self.tn = None

        self.tn.read_until("> ".encode(encoding='ascii'))
        time.sleep(1.)
        self.cmd_get_answare("")

    def solar_move(self, alt, azi):
        self.cmd_get_answare("sc {:.1f} {:.1f}".format(alt, azi))

    def set_ory(self, alt, azi):
        self.cmd_get_answare("set-ory {:.1f} {:.1f}".format(alt, azi))

    def get_id(self):
        ans = self.cmd_get_answare("id")
        try:
            assert ans is not None and len(ans) == 1
        except AssertionError:
            print("Wrong answare from id")
            return False
        return ans[0]

    def get_time(self):
        ans = self.cmd_get_answare('time')
        return Time(ans[1], format='isot')

    def set_geo(self, lat, lon):
        return self.cmd_get_answare('set-geo {:.3f} {:.3f}'.format(lat, lon)) is not None

    def set_prm(self, key:str, value):
        if key in HELIOS_INT_EDITABLE_CFG.values():
            ans = self.cmd_get_answare("set {:s} {:d}".format(key, value))
        else:
            ans = self.cmd_get_answare("set {:s} {:f}".format(key, value))
        try:
            assert ans is not None
        except AssertionError:
            print("Wrong answare from set")
            return False
        return True

    def get_geo(self):
        ans = self.cmd_get_answare("get-geo")
        try:
            assert ans is not None and len(ans) == 1
        except AssertionError:
            print("Wrong answare from get-geo")
            return False

        tok = ans[0].split()
        res = {}
        assert tok[0] == 'LAT:'
        res['lat'] = float(tok[1])
        assert tok[2] == 'LON:'
        res['lon'] = float(tok[3])
        self.lat = res['lat']
        self.lon = res['lon']
        return res

    def get_prm(self, key):
        ans = self.cmd_get_answare("get {:s}".format(key))
        try:
            assert ans is not None and len(ans) == 1
        except AssertionError:
            print("Wrong answare from get")
            return False
        s = ans[0].strip().split()[2]
        return float(s)

    def factory_reset(self):
        return self.cmd_get_answare('factory-reset') is not None

    def disconnect(self):
        self.cmd_get_answare('quit', maxlines=0)
        self.tn = None

    def alt_move(self, t, s):
        self.cmd_get_answare('alt-move {:d} {:d}'.format(t,s))

    def azi_move(self, t, s):
        self.cmd_get_answare('azi-move {:d} {:d}'.format(t,s))

    def get_cfg(self):
        ans = self.cmd_get_answare('configs')
        for a in ans:
            self.cfg[a.split()[0]] = float(a.split()[1])

    def reload_prm(self):
        ans = self.cmd_get_answare('reload-prm')

    def absolute_move(self, alt, azi):
        self.alt_setpoint = alt
        self.azi_setpoint = azi
        self.cmd_get_answare("mc {:.1f} {:.1f}".format(alt, azi))

    def stop_move(self):
        self.cmd_get_answare("stop")

    def driver_off(self):
        self.cmd_get_answare("driver-off")

    def driver_on(self):
        self.cmd_get_answare("driver-on")

    def test_scene(self, scene):
        self.cmd_get_answare("test-scene {:s}".format(scene))

    def sleep(self, nseconds):
        self.cmd_get_answare("sleep {:d}".format(nseconds))

    def get_status(self):
        ans = self.cmd_get_answare("status")
        res = {'ntp': False, 'rtc': False, 'adc': False, 'intrtc': False}
        if ans[0].startswith('NTP: OK'):
            res['ntp'] = True
        if ans[1].startswith('RTC: OK'):
            res['rtc'] = True
        if ans[2].startswith('internal RTC: OK'):
            res['intrtc'] = True
        if ans[3].startswith('external ADC: OK'):
            res['adc'] = True
        if ans[4].startswith('driver is ON'):
            res['driver'] = True
        else:
            res['driver'] = False
        return res

    def list_dir(self, dir):
        return [a.strip() for a in self.cmd_get_answare('ls {:s}'.format(dir))]

    def get_list_scene(self):
        ans = self.cmd_get_answare('list-scene')
        self.scenes = {}
        self.scenes_len = {}
        for s in ans:
            tok = s.strip().split()
            scene_id = int(tok[0][1:-1])
            scene_name = tok[1]
            scene_len = int(tok[2])
            self.scenes[scene_name] = scene_id
            self.scenes_len[scene_name] = scene_len * self.cfg['SCENE_DT']
        return self.scenes

    def scene_is_used(self, scene):
        for s in self.schedule:
            if s.type == 'sequence' and scene in s.sequence:
                return True
        return False

    def delete_scene(self, name):
        if name in self.scenes:
            scene_id = self.scenes[name]
            if self.scene_is_used(name):
                print("Scene is used!")
                return None
            self._remove_scene(scene_id)
            for sn in self.scenes:
                if self.scenes[sn] > scene_id:
                    self.scenes[sn] -= 1
            del self.scenes[name]
        else:
            print("Scene name wrong ", name)

    def get_scene(self, name):
        if name in self.scenes:
            return self._get_scene(self.scenes[name])

    def _new_scene(self, scene_name):
        ans = self.cmd_get_answare('new-scene {:s}'.format(scene_name))
        if ans is None:
            return None
        scene_id = int(ans[0].strip().split()[3])
        return scene_id

    def _remove_scene(self, scene_id):
        ans = self.cmd_get_answare('remove-scene {:d}'.format(scene_id))
        return ans is not None

    def _get_scene(self, scene_id):
        ans = self.cmd_get_answare('print-scene {:d}'.format(scene_id))
        if ans is None:
            return None
        s = []
        for fr in ans[1:]:
            fr_s = fr.strip().split()
            alt = float(fr_s[4])
            azi = float(fr_s[5])
            s += [[alt, azi]]

        return np.array(s)

    def _add_frame_to_scene(self, scene_id, alt, azi):
        ans = self.cmd_get_answare('add-frame-scene {:d} {:.1f} {:.1f}'.format(scene_id, alt, azi))
        return ans is not None

    def _save_scene(self, scene_id):
        ans = self.cmd_get_answare('write-scene {:d}'.format(scene_id))
        return ans is not None

    def upload_scene(self, scene_name, data):
        try:
            assert scene_name not in self.scenes
        except AssertionError:
            print("This scene name is already used")
        try:
            assert data.shape[0] <= 120 and data.shape[1] == 2
        except AssertionError:
            print("Data has wrong shape")
            return False
        scene_id = self._new_scene(scene_name)
        if scene_id is None:
            print("Error in scene creation")
            return False
        for fr in data:
            if self._add_frame_to_scene(scene_id, fr[0], fr[1]) is None:
                print("Error in uploading data")
                return False

        if not self._save_scene(scene_id):
            print("Error in saving")
            return False
        self.scenes[scene_name] = scene_id
        return True

    def get_position(self):
        ans = self.cmd_get_answare('current-position')

        try:
            assert ans is not None and len(ans) == 1
        except AssertionError:
            print("Wrong answare from current-position")
            return False

        tok = ans[0].split()
        assert tok[0] == 'ABSOLUTE'
        assert tok[1] == 'ALT'
        self.alt = float(tok[2])
        assert tok[3] == 'AZI'
        self.azi = float(tok[4])

        return [self.alt, self.azi]

    def sync_rtc_ntp(self):
        ans = self.cmd_get_answare('sync-rtc-ntp')
        return ans is not None

    def wifi_off(self):
        ans = self.cmd_get_answare('wifi-off', maxlines=0)
        self.tn = None

    def syslog(self):
        ans = self.cmd_get_answare('syslog')
        return [a.strip() for a in ans]

    def battery_charge(self):
        ans = self.cmd_get_answare('battery')
        if ans is None:
            return -1.
        return float(ans[0].strip().split()[0])

    def get_wifi_conn(self):
        self.wifi_conn = {}
        self.wifi_pass = {}

        ans = self.cmd_get_answare('print-wifi')
        for s in ans:
            tok = s.strip().split()
            wifi_id = int(tok[0][1:-1])
            ssid = tok[1]
            password = tok[2]

            self.wifi_conn[ssid] = wifi_id
            self.wifi_pass[ssid] = password

        return self.wifi_conn

    def add_wifi_network(self, ssid, password):
        self._add_wifi(ssid, password)
        self.get_wifi_conn()
        self._save_wifi()

    def delete_wifi_network(self, ssid):
        self._delete_wifi(self.wifi_conn[ssid])
        self.get_wifi_conn()
        self._save_wifi()

    def _add_wifi(self, ssid, password):
        ans = self.cmd_get_answare('add-wifi {:s} {:s}'.format(ssid, password))
        return ans is not None

    def _save_wifi(self):
        ans = self.cmd_get_answare('save-wifi')
        return ans is not None

    def _delete_wifi(self, wifi_id):
        ans = self.cmd_get_answare('delete-wifi {:d}'.format(wifi_id))
        return ans is not None

    def test_sequence(self, scenes):
        cmd = 'run-test-sequence '
        for s in scenes:
            try:
                assert s in self.scenes
            except AssertionError:
                print("Scene {:s} is not present".format(s))
                return None
            cmd += '{:s} '.format(s)
        ans = self.cmd_get_answare(cmd[:-1])
        return ans is not None

    def get_schedule(self):
        ans = self.cmd_get_answare('print-schedule')
        if ans is None:
            return False
        self.schedule = []
        for s in ans:
            tok = s.strip().split()
            if tok[1] == '*':
                self.schedule += [HeliosSchedule(int(tok[0][1:-1]), tok[4], tok[5], tok[6:])]
            else:
                self.schedule += [HeliosSchedule(int(tok[0][1:-1]), tok[4], tok[5], tok[6:], int(tok[1]), int(tok[2]), int(tok[3]))]
        self.schedule = sorted(self.schedule)
        return self.schedule

    def remove_schedule(self, s):
        self._remove_schedule(s)
        self._save_schedule()
        self.get_schedule()

    def add_schedule(self, s:HeliosSchedule):
        self._add_schedule(s.time.hour, s.time.minute, s.time.second, s.type, s.sequence, s.year, s.month, s.day)
        self._save_schedule()
        self.get_schedule()

    def _remove_schedule(self, sch):
        ans = self.cmd_get_answare('delete-schedule {:d}'.format(sch.id))
        return ans is not None

    def _add_schedule(self, h, m, s, sch_type, seq=[], year=None, month=None, day=None):
        ans = None
        if year is not None and month is not None and day is not None:
            dates = "{:04d} {:02d} {:02d}".format(year, month, day)
        else:
            dates = "0 0 0"

        if sch_type == 'wifi':
            ans = self.cmd_get_answare('add-task-wifi {:s} {:d} {:d} {:d}'.format(dates, h, m, s))
        elif sch_type == 'sequence' and len(seq) > 0:
            cmd = 'add-task-sequence {:s} {:d} {:d} {:d}'.format(dates, h, m, s)
            for i in seq:
                cmd += ' {:s}'.format(i)
            ans = self.cmd_get_answare(cmd)
        return ans is not None

    def _save_schedule(self):
        ans = self.cmd_get_answare('save-schedule')
        return ans is not None

    def check_sun_position(self, tol=1.0):
        ans = self.cmd_get_answare('mirror-log')
        assert ans[0].split()[0] == 'SUN'
        device_sun_alt = float(ans[1].split()[1])
        device_sun_azi = float(ans[1].split()[3])
        geoloc = self.get_geo()

        apy_azi, apy_alt = get_sun_position((self.lon, self.lat), ans[6].split()[2])
        try:
            assert abs(device_sun_alt - apy_alt)  < tol and abs(device_sun_azi - apy_azi) < tol
        except AssertionError:
            print(device_sun_alt, apy_alt)
            print(device_sun_azi, apy_azi)
            return False
        return True

    def get_ory(self):
        ans = self.cmd_get_answare('mirror-log')
        assert ans[2].split()[0] == 'OUT-RAY'
        ory_alt = float(ans[3].split()[1])
        ory_azi = float(ans[1].split()[3])
        return ory_alt, ory_azi

    def check_device_clock(self, tol=2.0):
        current_time = Time.now()
        device_time = self.get_time()

        delta = device_time-current_time
        try:
            assert delta.to_value('sec') < tol
        except AssertionError:
            print(device_time)
            print(current_time)
            return False
        return True

    def cmd_get_answare(self, cmd, maxlines=10):
        # Send a command through the socket, read the answare, if it is ok
        # return None if it is not OK

        print(cmd)
        if self.tn is None:
            return None

        self.tn.write("{:s}".format(cmd).encode())
        self.tn.write(b"\n")
        #print(self.socket.send("\r\n".encode()))
        ans = []
        for i in range(maxlines):
            try:
                tmpa = self.tn.read_until(b' > ')
            except:
                self.connect()
                self.tn.open(self.ip)
                return None
            print(tmpa.decode())
            for l in tmpa.decode().split('\n'):
                if l:
                    ans += [l]
            try:
                assert len(ans) < maxlines and ans[-1] != '[OK] > ' and ans[-1] != '[!!] > '
            except AssertionError:
                break

        if maxlines == 0:
            return None
        if ans[-1] == '[!!] > ':
            return None
        else:
            return ans[:-1]


if __name__ == "__main__":
    import sys
    hg = HeliosUnit(sys.argv[1])
    for s in hg.schedule:
        print(str(s))

    print(hg.scenes)
    print(str(HeliosSchedule(0, "06:30:00", 'sequence', ['circle.txt', 'circle.txt'])))
    print(hg.schedule)

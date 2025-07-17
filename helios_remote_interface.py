from tkinter import *
import tkinter.ttk as ttk
from ttkthemes import ThemedTk
from helios_interface import *
import matplotlib.pyplot as plt
import datetime
import numpy as np
import threading
import scipy
from functools import partial

def _create_circle(self, c, r, **kwargs):
    x = c[0]
    y = c[1]
    return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
Canvas.create_circle = _create_circle

def _set_text(self, text):
    self.config(state='normal')
    self.delete(0,END)
    self.insert(0,text)
    self.config(state='readonly')
    return
Entry.set = _set_text

def sc2a(s, c):
    a = np.asin(s)
    if(c < 0):
        a = np.pi -a
    return a

def absolute_to_geo(v):
    absolute_alt_cosine = np.sqrt(v[0] * v[0] + v[1] * v[1])
    absolute_alt_sine = v[2]
    absolute_alt = sc2a(absolute_alt_sine, absolute_alt_cosine)

    absolute_azi_sine = v[1] / absolute_alt_cosine
    absolute_azi_cosine = v[0] / absolute_alt_cosine
    absolute_azi = sc2a(absolute_azi_sine, absolute_azi_cosine)
    absolute_azi = 90.0 - absolute_azi * 180/np.pi;
    return absolute_alt * 180/np.pi, absolute_azi

def geo_to_absolute(alt, azi):
    azi_rad = azi * np.pi / 180.
    absolute_azi_rad = np.pi/2 - azi_rad
    absolute_alt_rad = alt * np.pi/180

    v = np.zeros(3)
    v[0] = np.cos(absolute_alt_rad) * np.cos(absolute_azi_rad)
    v[1] = np.cos(absolute_alt_rad) * np.sin(absolute_azi_rad)
    v[2] = np.sin(absolute_alt_rad)
    return v

def get_sun_unit_vec(loc, t):
    azi, alt = get_sun_position(loc, t)
    return geo_to_absolute(alt, azi)

def get_normal_vec(sun, ory):
    norm = np.dot(sun, ory)
    norm = -2 * np.sqrt((1+norm)/2.)
    mir = (-sun - ory)/norm
    return mir

def get_reflected_vec(sun, mir):
    norm = np.dot(mir, sun)
    ory = -sun + 2*norm*mir
    return ory

def ory2mir(alt, azi, loc, t):
    ory = geo_to_absolute(alt, azi)
    sun = get_sun_unit_vec(loc, t)
    
    mir = get_normal_vec(sun, ory)
    return absolute_to_geo(mir)

def mir2ory(alt, azi, loc, t):
    mir = geo_to_absolute(alt, azi)
    sun = get_sun_unit_vec(loc, t)
    ory = get_reflected_vec(sun, mir)
    return absolute_to_geo(ory)

class HeliosControlTab():
    def __init__(self, h, root):
        self.my_helios = h
        self.canva_h = 600
        self.canva_w = 900
        self.helios_canvas = None

        self.helios_is_ok = False
        stat = self.my_helios.get_status()
        if stat['adc'] and stat['rtc'] and stat['intrtc']:
            self.helios_is_ok = True

        self.mir_alt = self.my_helios.alt
        self.mir_azi = self.my_helios.azi
        if self.helios_is_ok:
            self.ory_alt, self.ory_azi = mir2ory(self.mir_alt, 
                                                 self.mir_azi,
                                                 (self.my_helios.lon, self.my_helios.lat), 
                                                 datetime.datetime.now(datetime.timezone.utc).isoformat()[:-6])
        
        self.helios_tab = ttk.Frame(root)

        self.control_mode = StringVar()
        self.scene_speed = DoubleVar()
        self.control_mode.set("dis")
        self.current_scene = np.array([])

        self.helios_canvas = Canvas(self.helios_tab, width=self.canva_w, height=self.canva_h, bg='white')
        self.pos_label = Label(self.helios_tab, text="Current Position")
        self.bat_label = Label(self.helios_tab, text="Battery Level")
        self.adc_label = Label(self.helios_tab, text="ADC OK")
        self.rtc_label = Label(self.helios_tab, text="ext RTC OK")
        self.intrtc_label = Label(self.helios_tab, text="int RTC OK")
        self.ntp_label = Label(self.helios_tab, text="NTP OFF")
        self.update_status_but = Button(self.helios_tab, text="Update", command=self.update_status)
        self.abs_control = Radiobutton(self.helios_tab, text="Absolute", variable=self.control_mode, value='abs')
        self.sol_control = Radiobutton(self.helios_tab, text="Solar", variable=self.control_mode, value='sol')
        self.dis_control = Radiobutton(self.helios_tab, text="Disabled", variable=self.control_mode, value='dis')
        self.calibrate_but = Button(self.helios_tab, text="Calibrate")
        self.add_pt_but = Button(self.helios_tab, text="Add Point to Scene", command=self.add_point_to_scene)
        self.test_scene_but = Button(self.helios_tab, text="Test Scene", command=self.test_scene)
        self.save_scene_but = Button(self.helios_tab, text="Save Scene", command=self.save_scene)
        self.clean_scene_but = Button(self.helios_tab, text="Clean Scene", command=self.clean_scene)
        self.load_scene_but = Button(self.helios_tab, text="Load Scene", command=self.dialog_load_scene)
        self.delete_scene_but = Button(self.helios_tab, text="Delete Scene", command=self.dialog_delete_scene)
        self.wifi_net_but = Button(self.helios_tab, text="Wifi Networks", command=self.dialog_wifi_net)
        self.sequence_but = Button(self.helios_tab, text="Sequences", command=self.dialog_sequence)
        self.calibrate_but = Button(self.helios_tab, text="Calibrate", command=self.dialog_calibrate)
        self.scene_speed_scale = ttk.Scale(self.helios_tab, from_=0, to=1., orient="horizontal", variable=self.scene_speed)


        self.pos_label.place(x=10, y=10)
        self.bat_label.place(x=10, y=30)
        self.adc_label.place(x=10, y=50)
        self.rtc_label.place(x=10, y=70)
        self.intrtc_label.place(x=10, y=90)
        self.ntp_label.place(x=10, y=110)
        self.update_status_but.place(x=10, y=130)
        self.wifi_net_but.place(x=10, y=200)
        self.calibrate_but.place(x=10, y=240)

        self.helios_canvas.place(x=150, y=10)

        self.sol_control.place(x=1110, y=10) 
        self.abs_control.place(x=1160, y=10)
        self.dis_control.place(x=1110, y=30)
        self.add_pt_but.place(x=1110, y=70)
        self.scene_speed_scale.place(x=1110, y=110)
        self.save_scene_but.place(x=1110, y=270)
        self.test_scene_but.place(x=1110, y=150)
        self.clean_scene_but.place(x=1110, y=190)
        self.load_scene_but.place(x=1110, y=230)
        self.delete_scene_but.place(x=1110, y=310)
        self.sequence_but.place(x=1110, y=350)
        
        self.draw_canvas_control()
        self.update_status()
      
    def a2c(self, alt, azi):
        if alt < -90:
            alt += 360
        if alt > 90:
            alt -= 360
        y = self.canva_h-(alt+90)/180.0 * self.canva_h
        if azi < 0:
            azi +=  360.
        x = (azi/360.0) * self.canva_w
        return x, y 
    
    def draw_canvas_background(self):
        # Horizontal grid
        #Horizon
        
        self.helios_canvas.create_line(self.a2c(0, 0), self.a2c(0, 360), width=2, fil='red')
        for i in range(-90, 90, 30):
            if i % 90 != 0:
                self.helios_canvas.create_line(self.a2c(i, 0), self.a2c(i, 360), width=1, fil='black')

        #Vertical grid
        for i in range(0, 360, 90):
            self.helios_canvas.create_line(self.a2c(-90, i), self.a2c(90, i), width=2, fil='red')
        for i in range(0, 360, 30):
            if i % 90 != 0:
                self.helios_canvas.create_line(self.a2c(-90, i), self.a2c(90, i), width=1, fil='black')


    def draw_canvas_control(self):
        if self.helios_canvas is None:
            return
        self.draw_canvas_background()

        sun_azi, sun_alt = get_sun_position((self.my_helios.lon, self.my_helios.lat), datetime.datetime.now(datetime.timezone.utc).isoformat()[:-6]) 
        self.helios_canvas.create_circle(self.a2c(sun_alt, sun_azi), 20, fill='yellow', outline='orange')

        if self.helios_is_ok:
            if self.control_mode.get() == 'sol':
                self.mir_alt, self.mir_azi = ory2mir(self.ory_alt, 
                                                    self.ory_azi,
                                                    (self.my_helios.lon, self.my_helios.lat), 
                                                    datetime.datetime.now(datetime.timezone.utc).isoformat()[:-6])
            elif self.control_mode.get() == 'abs' or self.control_mode.get() == 'dis':
                self.ory_alt, self.ory_azi = mir2ory(self.mir_alt, 
                                                    self.mir_azi,
                                                    (self.my_helios.lon, self.my_helios.lat), 
                                                    datetime.datetime.now(datetime.timezone.utc).isoformat()[:-6])
            
            self.helios_canvas.create_circle(self.a2c(self.ory_alt, self.ory_azi), 5, fill='black', outline='blue')
            self.helios_canvas.create_circle(self.a2c(self.mir_alt, self.mir_azi), 10,  fill="#BBB", outline="")

        if self.current_scene.shape[0] > 0:
            for pt in range(self.current_scene.shape[0]):
                self.helios_canvas.create_circle(self.a2c(self.current_scene[pt][0], self.current_scene[pt][1]), 5, fill='green', outline='green')
            
            interp_data = self.interp_helios()
            for pt in range(interp_data.shape[0]):
                self.helios_canvas.create_circle(self.a2c(interp_data[pt][0], interp_data[pt][1]), 2, fill='red', outline='red')

    def update(self):
        self.helios_canvas.delete("all")
        self.draw_canvas_control()

    def update_status(self):
        s = self.my_helios.get_status()
        if s['adc']:
            self.adc_label.config(text = "ADC OK")
        else:
            self.adc_label.config(text = "ADC NOT OK")
        if s['rtc']:
            self.rtc_label.config(text = "RTC OK")
        else:
            self.rtc_label.config(text = "RTC NOT OK")
        if s['intrtc']:
            self.intrtc_label.config(text = "intRTC OK")
        else:
            self.intrtc_label.config(text = "intRTC NOT OK")
        if s['ntp']:
            self.ntp_label.config(text = "NTP OK")
        else:
            self.ntp_label.config(text = "NTP NOT OK")
        self.my_helios.get_position()
        self.pos_label.config(text = "{:.1f} {:.1f}".format(self.my_helios.alt, self.my_helios.azi))
        bat_lev = self.my_helios.battery_charge()
        self.bat_label.config(text = "BAT {:.0f} %".format(bat_lev))

    def add_point_to_scene(self):
        size = self.current_scene.shape[0]
        if size >= self.my_helios.sequence_max:
            return
        tmp = self.current_scene.copy()
        self.current_scene = np.zeros((size+1, 2))
        if size > 0:
            self.current_scene[:size] = tmp
        if self.ory_alt > 180.:
            self.current_scene[size] = [self.ory_alt-360., self.ory_azi]
        else:
            self.current_scene[size] = [self.ory_alt, self.ory_azi]
        print(self.current_scene)

    def interp_helios(self):
        s = self.scene_speed.get()
        dat = self.current_scene

        if dat.shape[0] <= 3:
            k = dat.shape[0] - 1
        else:
            k=3
        
        if dat.shape[0] == 1:
            smax = self.my_helios.sequence_dt
        else:
            smax = (self.my_helios.sequence_max - 1) * self.my_helios.sequence_dt / (dat.shape[0]-1)
        smin = self.my_helios.sequence_dt
        dt = smin + s*(smax-smin)
        nout = int((dat.shape[0]-1)*dt // self.my_helios.sequence_dt  + 1)
        
        inter = scipy.interpolate.make_interp_spline(np.arange(0, dat.shape[0], 1.0) * dt, dat, k=k)
        c = inter(np.arange(0, (dat.shape[0]-1)*dt, self.my_helios.sequence_dt))
        c = np.concatenate((c, dat[-1:,:]))
        speed_alt = 0
        speed_azi = 0
        for i in range(1, nout):
            sazi = abs(c[i,0]-c[i-1,0]) / dt
            salt = abs(c[i,1]-c[i-1,1]) / dt
            if sazi > speed_azi:
                speed_azi = sazi
            if salt > speed_alt:
                speed_alt = salt
        return c
    
    
    def test_scene(self):
        if self.current_scene.shape[0] == 0:
            return
        self.my_helios.upload_scene('test', self.interp_helios())
        self.my_helios.test_scene('test')
        self.my_helios.delete_scene('test')
    
    def clean_scene(self):
        self.current_scene = np.array([])
        self.my_helios.delete_scene('test')

    def dialog_load_scene(self):
        dialog = Toplevel()
        dialog.wm_title("Load Scene from Helios...")
        
        def dialog_load_act(sn):
            self.current_scene = self.my_helios.get_scene(sn)
            dialog.destroy()

        for i, s in enumerate(self.my_helios.scenes.keys()):
            a = partial(dialog_load_act, s)
            b = Button(dialog, text=s, command=a)
            b.grid(row=i//3, column=i%3, padx=10, pady=10)

        Button(dialog, text="Cancel", command=dialog.destroy).grid(row=len(self.my_helios.scenes.keys())//3+1, 
                                                                   column=1, 
                                                                   padx=10, pady=10)
    
    def save_scene(self):
        if self.current_scene.shape[0] == 0:
            return
        dialog = Toplevel()
        dialog.wm_title("Save Scene to Helios...")
        
        def dialog_save_act():
            self.my_helios.upload_scene(name_field.get(), self.interp_helios())
            dialog.destroy()

        name_field = Entry(dialog, width=16)
        name_field.grid(row=1, column=1, padx=10, pady=10)
        Button(dialog, text="Save", command=dialog_save_act).grid(row=2, column=1, padx=10, pady=10)
        Button(dialog, text="Cancel", command=dialog.destroy).grid(row=2, column=2, padx=10, pady=10)

    def dialog_delete_scene(self):
        dialog = Toplevel()
        dialog.wm_title("Delete Scene from Helios...")
        
        def dialog_delete_act(sn):
            print(sn)
            self.my_helios.delete_scene(sn)
            dialog.destroy()

        for i, s in enumerate(self.my_helios.scenes.keys()):
            a = partial(dialog_delete_act, s)
            b = Button(dialog, text=s, command=a)
            b.grid(row=i//3, column=i%3, padx=10, pady=10)
        
        Button(dialog, text="Cancel", command=dialog.destroy).grid(row=len(self.my_helios.scenes.keys())//3+1, 
                                                                   column=1, 
                                                                   padx=10, pady=10)
        
    def dialog_wifi_net(self):
        dialog = Toplevel()
        dialog.wm_title("Manage Helios WiFi Network")
        
        def dialog_delete_act(sn):
            self.my_helios.delete_wifi_network(sn)
            dialog.destroy()

        def dialog_add_act():
            self.my_helios.add_wifi_network(ssid_entry.get(), pass_entry.get())
            dialog.destroy()

        for i, s in enumerate(self.my_helios.wifi_conn.keys()):
            Label(dialog, text=s).grid(row=i, column=0)
            a = partial(dialog_delete_act, s)
            Button(dialog, text="Remove", command=a).grid(row=i, column=1, 
                                                                                     padx=10, pady=10)
        row = len(self.my_helios.wifi_conn)
        
        ttk.Separator(dialog,orient=HORIZONTAL).grid(row=row, columnspan=3, sticky="ew")

        Label(dialog, text="SSID").grid(row=row+1, column=0, padx=10, pady=10)
        Label(dialog, text="Password").grid(row=row+1, column=1, padx=10, pady=10)
        
        ssid_entry = Entry(dialog, width=20)
        ssid_entry.grid(row=row+2, column=0, padx=10, pady=10)
        pass_entry = Entry(dialog, width=20)
        pass_entry.grid(row=row+2, column=1, padx=10, pady=10)
        Button(dialog, text="Add", command=dialog_add_act).grid(row=row+3, 
                                                                column=0, 
                                                                padx=10, pady=10)
    
        Button(dialog, text="Cancel", command=dialog.destroy).grid(row=row+3, 
                                                                   column=1, 
                                                                   padx=10, pady=10)
        
    def dialog_sequence(self):
        dialog = Toplevel()
        dialog.wm_title("Manage Helios Sequence Schedule")
        
        def dialog_delete_act(s):
            self.my_helios.remove_schedule(s)
            dialog.destroy()

        def dialog_add_act():
            dt = datetime.datetime.fromisoformat("1900-01-01 {:02d}:{:02d}:{:02d}".format(int(h_entry.get()), int(m_entry.get()), int(s_entry.get())))
            tz_delta = datetime.datetime.now(datetime.timezone.utc).astimezone().utcoffset()
            utc_time = (dt-tz_delta).time()
            hs = HeliosSchedule(0, str(utc_time), 'sequence', seq.get().split())
            self.my_helios.add_schedule(hs)
            dialog.destroy()

        def dialog_add_scene_act(s):
            seq.set(seq.get()+' '+s)

        def dialog_remove_scene_act():
            seq.set(' '.join(seq.get().split()[:-1]))

        i = 0
        for s in self.my_helios.schedule:
            if s.type == 'wifi':
                continue
            if (i%2)*2 == 0:
                cs = 5
                col = 0
            else:
                cs = 1
                col = 5
            Label(dialog, text=str(s)[4:]).grid(row=i//2, column=(i%2)*2+6)
            a = partial(dialog_delete_act, s)
            Button(dialog, text="Remove", command=a).grid(row=i//2, column=(i%2)*2+col, padx=10, pady=10,columnspan=cs)
            i += 1
  
        row = i
        ttk.Separator(dialog,orient=HORIZONTAL).grid(row=row, columnspan=9, sticky="ew")

        seq = Entry(dialog, text="DIOLUPO", width=150, state='readonly')
        seq.grid(row=row+1, column=6, columnspan=3, padx=10, pady=10)
        
        h_entry = Entry(dialog, width=2)
        h_entry.grid(row=row+1, column=0, padx=0, pady=10)
        Label(dialog, text=":").grid(row=row+1, column=1, padx=0, pady=10)
        m_entry = Entry(dialog, width=2)
        m_entry.grid(row=row+1, column=2, padx=0, pady=0)
        Label(dialog, text=":").grid(row=row+1, column=3, padx=0, pady=10)
        s_entry = Entry(dialog, width=2)
        s_entry.grid(row=row+1, column=4, padx=0, pady=10)

        for i, s in enumerate(self.my_helios.scenes.keys()):
            if (i%4)*2 == 0:
                cs = 5
                col = 0
            else:
                cs = 1
                col = 5
            a = partial(dialog_add_scene_act, s)
            b = Button(dialog, text=s, command=a)
            print(s, i%4+col)
            b.grid(row=row+2+i//4, column=i%4+col, columnspan=cs, padx=10, pady=10)

        Button(dialog, text="Add Seq", command=dialog_add_act).grid(row=row+3, 
                                                                column=0,
                                                                columnspan=5, 
                                                                padx=10, pady=10)
        Button(dialog, text="Remove Scene", command=dialog_remove_scene_act).grid(row=row+3, 
                                                                column=6,
                                                                padx=10, pady=10)
    
        Button(dialog, text="Cancel", command=dialog.destroy).grid(row=row+3, 
                                                                   column=7, 
                                                                   padx=10, pady=10)
        
    def dialog_calibrate(self):
        dialog = Toplevel()
        dialog.wm_title("Calibrate Helios")
        
        def _read_enc():
            self.my_helios.get_position()
            lab_altazi_1.config(text="ALT {:+06.1f} AZI {:+06.1f}".format(self.my_helios.alt, self.my_helios.azi))
        Label(dialog,
              text=
              """1. Check that the motors are running in the correct way, that 
                    is clockwise for azi and to up for alt, try to move and then read the 
                    encoders to ensure that everything is correct.  If not please switch 
                    motor connection.""", width=80, wraplength=600).grid(row=0, column=0, columnspan=4, padx=10, pady=10)
        Button(dialog, text="Alt +", command=lambda :self.my_helios.alt_move(1000, int(self.my_helios.cfg['PWM_MAX_VALUE']))).grid(row=1, column=0, padx=10, pady=10)
        Button(dialog, text="Alt -", command=lambda :self.my_helios.alt_move(1000, -int(self.my_helios.cfg['PWM_MAX_VALUE']))).grid(row=1, column=1, padx=10, pady=10)
        Button(dialog, text="Azi +", command=lambda :self.my_helios.azi_move(1000, int(self.my_helios.cfg['PWM_MAX_VALUE']))).grid(row=1, column=2, padx=10, pady=10)
        Button(dialog, text="Azi -", command=lambda :self.my_helios.azi_move(1000, -int(self.my_helios.cfg['PWM_MAX_VALUE']))).grid(row=1, column=3, padx=10, pady=10)
        Button(dialog, text="Read encoders", command=_read_enc).grid(row=2, column=1, padx=10, pady=10)
        lab_altazi_1 = Label(dialog, text="ALT ------ AZI ------")
        lab_altazi_1.grid(row=2, column=2, padx=10, pady=10)
        ttk.Separator(dialog, orient=HORIZONTAL).grid(row=3, column=0, columnspan=4)

        Label(dialog,
              text=
              """2. Go to zero as precisely as possible (especially for alt).""", 
              width=80, wraplength=600).grid(row=4, column=0, columnspan=4, padx=10, pady=10)
        def _set_alt_e0():
            self.my_helios.get_position()
            alte0 = self.my_helios.alt + self.my_helios.get_prm("alte0")
            if(alte0 > 360):
                alte0 -= 360
            if(alte0 < 0 ):
                alte0 += 360
            self.my_helios.set_prm("alte0", alte0)
            self.my_helios.reload_prm()
        def _set_azi_e0():
            self.my_helios.get_position()
            azie0 = self.my_helios.azi + self.my_helios.get_prm("azie0")
            if(azie0 > 360):
                azie0 -= 360
            if(azie0 < 0 ):
                azie0 += 360
            self.my_helios.set_prm("azie0", azie0)
            self.my_helios.reload_prm()

        speed_2_alt = DoubleVar()
        speed_2_azi = DoubleVar()
        Button(dialog, text="Alt +", command=lambda :self.my_helios.alt_move(int(speed_2_alt.get()), int(self.my_helios.cfg['PWM_MAX_VALUE']))).grid(row=5, column=0, padx=10, pady=10)
        Button(dialog, text="Alt -", command=lambda :self.my_helios.alt_move(int(speed_2_alt.get()), -int(self.my_helios.cfg['PWM_MAX_VALUE']))).grid(row=5, column=1, padx=10, pady=10)
        Button(dialog, text="Azi +", command=lambda :self.my_helios.azi_move(int(speed_2_azi.get()), int(self.my_helios.cfg['PWM_MAX_VALUE']))).grid(row=5, column=2, padx=10, pady=10)
        Button(dialog, text="Azi -", command=lambda :self.my_helios.azi_move(int(speed_2_azi.get()), -int(self.my_helios.cfg['PWM_MAX_VALUE']))).grid(row=5, column=3, padx=10, pady=10)
        Label(dialog, text="Alt Speed").grid(row=6, column=0, padx=10, pady=10)
        ttk.Scale(dialog, from_=10, to=1000, orient="horizontal", variable=speed_2_alt).grid(row=6, column=1, padx=10, pady=10)
        Label(dialog, text="Alt Speed").grid(row=6, column=2, padx=10, pady=10)
        ttk.Scale(dialog, from_=10, to=1000, orient="horizontal", variable=speed_2_azi).grid(row=6, column=3, padx=10, pady=10)
        Button(dialog, text="Set Alt Zero", command=_set_alt_e0).grid(row=7, column=0, columnspan=2, padx=10, pady=10)
        Button(dialog, text="Set Azi Zero", command=_set_azi_e0).grid(row=7, column=2, columnspan=2, padx=10, pady=10)
        ttk.Separator(dialog, orient=HORIZONTAL).grid(row=8, column=0, columnspan=4)

        Label(dialog,
              text=
              """3. Now I will try to go at 90.0 degrees on alt axis and on azi axis, 
                 you should then correct the real position (eg using a bubble) and finally,
                 ask to set the corrections (if precision resistor are used this should not
                 needed).""", 
              width=80, wraplength=600).grid(row=9, column=0, columnspan=4, padx=10, pady=10)
        speed_3_alt = DoubleVar()
        speed_3_azi = DoubleVar()

        def _alt_v2d_corr():
            self.my_helios.get_position()
            v2d = self.my_helios.get_prm('altv2d')
            v2d *= self.my_helios.alt/90.
            self.my_helios.set_prm('altv2d', v2d)

        def _azi_v2d_corr():
            self.my_helios.get_position()
            v2d = self.my_helios.get_prm('aziv2d')
            v2d *= self.my_helios.azi/90.
            self.my_helios.set_prm('aziv2d', v2d)

        Button(dialog, text="Go to 90.0 90.0", command=lambda :self.my_helios.absolute_move(90., 90.)).grid(row=10, column=0, columnspan=4, padx=10, pady=10)
        Button(dialog, text="Alt +", command=lambda :self.my_helios.alt_move(int(speed_3_alt.get()), int(self.my_helios.cfg['PWM_MAX_VALUE']))).grid(row=11, column=0, padx=10, pady=10)
        Button(dialog, text="Alt -", command=lambda :self.my_helios.alt_move(int(speed_3_alt.get()), -int(self.my_helios.cfg['PWM_MAX_VALUE']))).grid(row=11, column=1, padx=10, pady=10)
        Button(dialog, text="Azi +", command=lambda :self.my_helios.azi_move(int(speed_3_azi.get()), int(self.my_helios.cfg['PWM_MAX_VALUE']))).grid(row=11, column=2, padx=10, pady=10)
        Button(dialog, text="Azi -", command=lambda :self.my_helios.azi_move(int(speed_3_azi.get()), -int(self.my_helios.cfg['PWM_MAX_VALUE']))).grid(row=11, column=3, padx=10, pady=10)
        Label(dialog, text="Alt Speed").grid(row=12, column=0, padx=10, pady=10)
        ttk.Scale(dialog, from_=10, to=1000, orient="horizontal", variable=speed_3_alt).grid(row=12, column=1, padx=10, pady=10)
        Label(dialog, text="Alt Speed").grid(row=12, column=2, padx=10, pady=10)
        ttk.Scale(dialog, from_=10, to=1000, orient="horizontal", variable=speed_3_azi).grid(row=12, column=3, padx=10, pady=10)
        Button(dialog, text="Set Alt Correction", command=_alt_v2d_corr).grid(row=13, column=0, columnspan=2, padx=10, pady=10)
        Button(dialog, text="Set Azi Correction", command=_azi_v2d_corr).grid(row=13, column=2, columnspan=2, padx=10, pady=10)
        ttk.Separator(dialog, orient=HORIZONTAL).grid(row=14, column=0, columnspan=4)

        Label(dialog,
              text=
              """4. Find out minimum and maximum speed parameters for the system. This is automatic,
                 the unit will move a bit...""", 
              width=80, wraplength=600).grid(row=15, column=0, columnspan=4, padx=10, pady=10)

        def _calibrate_speed():
            h = self.my_helios
            h.absolute_move(h.get_prm('alte0')+180, h.get_prm('azie0')+180)

            def azi_move_get_speed(pwm, t=2):
                azi0 = h.get_position()[1]
                h.azi_move(t*1000, pwm)
                azi1 = h.get_position()[1]
                if azi1 < azi0:
                    azi1 += 360
                h.azi_move(t*1000, -pwm)
                return (azi1-azi0) / t
            
            def alt_move_get_speed(pwm, t=2):
                alt0 = h.get_position()[0]
                h.alt_move(t*1000, pwm)
                alt1 = h.get_position()[0]
                if alt1 < alt0:
                    alt1 += 360
                h.alt_move(t*1000, -pwm)
                return (alt1-alt0) / t
            
            azi_max_angular_speed = azi_move_get_speed(int(self.my_helios.cfg['PWM_MAX_VALUE']))
            alt_max_angular_speed = alt_move_get_speed(int(self.my_helios.cfg['PWM_MAX_VALUE']))
            h.set_prm("alt_Msv", alt_max_angular_speed)
            h.set_prm("azi_Msv", azi_max_angular_speed)

            for pwm in range(int(self.my_helios.cfg['PWM_MAX_VALUE']), 0, -10):
                if alt_move_get_speed(pwm) < 2.0:
                    alt_min_speed_pwm = pwm
                    break
            for pwm in range(alt_min_speed_pwm, int(self.my_helios.cfg['PWM_MAX_VALUE'])):
                if alt_move_get_speed(pwm, t=5) > .5:
                    alt_min_speed_pwm = pwm
                    break

            for pwm in range(int(self.my_helios.cfg['PWM_MAX_VALUE']), 0, -10):
                if azi_move_get_speed(pwm) < 2.0:
                    azi_min_speed_pwm = pwm
                    break
            for pwm in range(azi_min_speed_pwm, int(self.my_helios.cfg['PWM_MAX_VALUE'])):
                if azi_move_get_speed(pwm, t=5) > .5:
                    azi_min_speed_pwm = pwm
                    break

            data = []
            for pwm in range(alt_min_speed_pwm, int(self.my_helios.cfg['PWM_MAX_VALUE']), 5):
                data += [[pwm, alt_move_get_speed(pwm, t=3)]]

            data = np.array(data)
            alts2p = np.polyfit(data[:,1], data[:,0], 1)[0]
            h.set_prm("alt_s2p", alts2p)

            data = []
            for pwm in range(azi_min_speed_pwm, int(self.my_helios.cfg['PWM_MAX_VALUE']), 5):
                data += [[pwm, azi_move_get_speed(pwm, t=3)]]

            data = np.array(data)
            azis2p = np.polyfit(data[:,1], data[:,0], 1)[0]
            h.set_prm("azi_s2p", azis2p)

        Button(dialog, text="Start", command=_calibrate_speed).grid(row=16, column=0, columnspan=4, padx=10, pady=10)

        Label(dialog,
              text=
              """5. Set Latitude and Longitude of your location""", 
              width=80, wraplength=600).grid(row=17, column=0, columnspan=4, padx=10, pady=10)
        speed_3_alt = DoubleVar()
        speed_3_azi = DoubleVar()

        lat_entry = Entry(dialog, text="0.000 LAT")
        lat_entry.grid(row=19, column=0, padx=10, pady=10)
        lon_entry = Entry(dialog, text="0.000 LON")
        lon_entry.grid(row=19, column=1, padx=10, pady=10)
        Button(dialog, text="Set", command=lambda :self.my_helios.set_geo(float(lat_entry.get()), float(lon_entry.get()))).grid(row=19, column=3, columnspan=2, padx=10, pady=10)


    

class HeliosGUI():
    def __init__(self):
        self.FRAMERATE = 100
        self.helios = []

        self.window = ThemedTk(theme="adapta")
        self.window.title("Helios Remote Control")
        self.window.geometry('1300x700')
        
        # MenuBar
        self.menubar = Menu(self.window)
        self.window.config(menu=self.menubar)

        self.helios_menu = Menu(self.menubar, tearoff=0)

        self.helios_menu.add_command(label='Add Unit', command=self.dialog_add_helios_unit)
        self.helios_menu.add_separator()

        self.helios_menu.add_command(label='Exit',command=self.quit)
        self.menubar.add_cascade(label="Helios", menu=self.helios_menu)

        self.window.bind("<Right>", self.right_arrow)
        self.window.bind("<Left>", self.left_arrow)
        self.window.bind("<Up>", self.up_arrow)
        self.window.bind("<Down>", self.down_arrow)

        self.add_unit_dialog = None
        self.add_unit_dialog_entry_ip = None

        self.quit_btn = None
        self.from_file = None
        self.main_tab = None
        self.helios_tabs = []

        self.update_position = False
        self.last_update_thread = None

        self.draw_main_space()

        self.window.after(1000, self.send_motor_cmd)
        self.window.after(self.FRAMERATE, self.update)
        self.window.after(30000, self.keep_helios_alive)

    def destroy_main_space(self):
        if self.quit_btn is not None:
            self.quit_btn.destroy()
        if self.from_file is not None:
            self.from_file.destroy()
        if self.main_tab is not None:
            self.main_tab.destroy()
        self.helios_tabs = []

    def draw_main_space(self):
        self.destroy_main_space()

        if(len(self.helios) == 0):
            self.quit_btn = ttk.Button(self.window, 
                                    text="Add First Helios Unit", 
                                    command=self.dialog_add_helios_unit)
            self.from_file = ttk.Button(self.window, 
                                        text="Load from File", 
                                        command=self.add_helios_from_file)
            self.quit_btn.place(relx=0.25, rely=0.5, anchor=CENTER)
            self.from_file.place(relx=0.75, rely=0.5, anchor=CENTER)
        else:
            self.main_tab = ttk.Notebook(self.window)
            self.helios_tabs = []
            for h in self.helios:
                self.helios_tabs += [HeliosControlTab(h, self.main_tab)]
                self.main_tab.add(self.helios_tabs[-1].helios_tab, text=h.id)

            self.main_tab.pack(expand = 1, fill ="both")



    def dialog_add_helios_unit(self):
        self.add_unit_dialog = Toplevel()
        self.add_unit_dialog.wm_title("Add Helios Unit...")
        l = Label(self.add_unit_dialog, text="Insert Unit's IP address: ")
        l.pack()
        self.add_unit_dialog_entry_ip = Entry(self.add_unit_dialog, width=16)
        self.add_unit_dialog_entry_ip.pack()
        b_ok = Button(self.add_unit_dialog, 
                      text="OK", 
                      command=self.add_helios_unit)
        b_ok.pack()
        b_cancel = Button(self.add_unit_dialog, text="Cancel", command=self.add_unit_dialog.destroy)
        b_cancel.pack()

    def add_helios_from_file(self):
        with open('helios.config') as f:
            for l in f:
                self.add_helios_unit(l.strip())

    def add_helios_unit(self, ip=None):
        if ip is None:
            if self.add_unit_dialog_entry_ip is not None:
                ip = self.add_unit_dialog_entry_ip.get()
            else:
                ip = ''
        self.helios += [HeliosUnit(ip)]
        if ip is None:
            self.add_unit_dialog.destroy()
        self.draw_main_space()

    def right_arrow(self, event):
        if len(self.helios) == 0:
            return
        else:
            speed = 2
            h_idx = self.main_tab.index(self.main_tab.select())
            h = self.helios[h_idx]
            tab = self.helios_tabs[h_idx]
            cm = tab.control_mode.get()
            if cm == 'sol':
                tab.ory_azi += speed
                if tab.ory_azi > 360.:
                    tab.ory_azi -= 360

            elif cm == 'abs':
                tab.mir_azi += speed
                if tab.mir_azi > 360.:
                    tab.mir_azi -= 360

            self.update_position = True

    def left_arrow(self, event):
        if len(self.helios) == 0:
            return
        else:
            speed = 2
            h_idx = self.main_tab.index(self.main_tab.select())
            h = self.helios[h_idx]
            tab = self.helios_tabs[h_idx]
            cm = tab.control_mode.get()
            if cm == 'sol':
                tab.ory_azi -= speed
                if tab.ory_azi < 0.:
                    tab.ory_azi += 360

            elif cm == 'abs':
                tab.mir_azi -= speed
                if tab.mir_azi < 0.:
                    tab.mir_azi += 360

            self.update_position = True

    def up_arrow(self, event):
        if len(self.helios) == 0:
            return
        else:
            speed = 2
            h_idx = self.main_tab.index(self.main_tab.select())
            h = self.helios[h_idx]
            tab = self.helios_tabs[h_idx]
            cm = tab.control_mode.get()
            if cm == 'sol':
                tab.ory_alt += speed
                if tab.ory_alt > 360.:
                    tab.ory_alt -= 360

                if tab.ory_alt > 90.0 and tab.ory_alt < 180:
                    tab.ory_alt = 90.

            elif cm == 'abs':
                tab.mir_alt += speed
                if tab.mir_alt > 360.:
                    tab.mir_alt -= 360

                if tab.mir_alt > 90.0 and tab.mir_alt < 180:
                    tab.mir_alt = 90.

            self.update_position = True

    def down_arrow(self, event):
        if len(self.helios) == 0:
            return
        else:
            speed = 2
            h_idx = self.main_tab.index(self.main_tab.select())
            h = self.helios[h_idx]
            tab = self.helios_tabs[h_idx]
            cm = tab.control_mode.get()
            if cm == 'sol':
                tab.ory_alt -= speed
                if tab.ory_alt < 0.:
                    tab.ory_alt += 360

                if tab.ory_alt < 270.0 and tab.ory_alt >= 180:
                    tab.ory_alt = 270

            elif cm == 'abs':
                tab.mir_alt -= speed
                if tab.mir_alt < 0.:
                    tab.mir_alt += 360

                if tab.mir_alt < 270.0 and tab.mir_alt >= 180:
                    tab.mir_alt = 270

            self.update_position = True


    def update(self):
        if len(self.helios) == 0:
            pass
        else:
            h_idx = self.main_tab.index(self.main_tab.select())
            h = self.helios[h_idx]
            self.helios_tabs[h_idx].update()
            
        self.window.after(self.FRAMERATE, self.update)

    def send_motor_cmd(self):
        if self.update_position:
            self.update_position = False
            print("send mot control")
            if self.last_update_thread is None or not self.last_update_thread.is_alive():
                h_idx = self.main_tab.index(self.main_tab.select())
                h = self.helios[h_idx]
                tab = self.helios_tabs[h_idx]
                cm = tab.control_mode.get()
                print("cm")
                if cm == 'sol':
                    thr = threading.Thread(target=h.solar_move, args=(tab.ory_alt, tab.ory_azi))
                elif cm == 'abs':
                    thr = threading.Thread(target=h.absolute_move, args=(tab.mir_alt, tab.mir_azi))
                elif cm == 'dis':
                    return
                thr.start() 
                self.last_update_thread  = thr
        self.window.after(250, self.send_motor_cmd)

    def keep_helios_alive(self):
        print('keep alive')
        for h in self.helios:
            print(h.id)
            h.cmd_get_answare("")
        self.window.after(30000, self.keep_helios_alive)


    def main_loop(self):
        self.window.mainloop()

    def quit(self):
        self.window.destroy()

if __name__ == "__main__":
    hgui = HeliosGUI()
    hgui.main_loop()


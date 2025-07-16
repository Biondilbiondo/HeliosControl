from tkinter import *
import tkinter.ttk as ttk
from ttkthemes import ThemedTk
from helios_interface import *
import matplotlib.pyplot as plt
import datetime
import numpy as np
import threading

def _create_circle(self, c, r, **kwargs):
    x = c[0]
    y = c[1]
    return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
Canvas.create_circle = _create_circle

def get_sun_unit_vec(loc, t):
    azi, alt = get_sun_position(loc, t)
    alt *= np.pi/180
    azi *= np.pi/180

    u = [np.cos(np.pi/2-azi) * np.cos(alt),
         np.sin(np.pi/2-azi) * np.cos(alt),
         np.sin(alt)]

    return np.array(u)

# o = i - 2(i . s) s
def get_reflection_vec(i, s):
    o = i - 2 * np.dot(i, s) * s
    # print(np.arccos(np.dot(i,o))*360/6.28)
    # print(np.arccos(np.dot(s,-i))*360/6.28)
    # print(np.arccos(np.dot(s,o))*360/6.28)
    return o


    sun = get_sun_unit_vec(loc, now)

def get_reflected_point(h:HeliosUnit):
    sun = get_sun_unit_vec((h.lon, h.lat), datetime.datetime.now(datetime.timezone.utc).isoformat()[:-6])
    malt = h.alt_setpoint * np.pi / 180.
    mazi = h.azi_setpoint * np.pi / 180.
    mir = [np.cos(np.pi/2-mazi) * np.cos(malt),
           np.sin(np.pi/2-mazi) * np.cos(malt),
           np.sin(malt)]
    mir = np.array(mir)

    back = get_reflection_vec(-sun, mir)
    #print(back)

    return 0, 0
class HeliosControlTab():
    def __init__(self, h, root):
        self.my_helios = h
        self.canva_h = 600
        self.canva_w = 900
        self.helios_canvas = None
        
        self.helios_tab = ttk.Frame(root)

        self.control_mode = StringVar()
        self.control_mode.set("sol")
        self.current_scene = np.array([[]])

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
        self.calibrate_but = Button(self.helios_tab, text="Calibrate")
        self.add_pt_but = Button(self.helios_tab, text="Add Point to Scene")
        self.test_scene_but = Button(self.helios_tab, text="Test Scene")
        self.save_scene_but = Button(self.helios_tab, text="Save Scene")
        self.clean_scene_but = Button(self.helios_tab, text="Clean Scene")
        self.load_scene_but = Button(self.helios_tab, text="Load Scene")


        self.pos_label.place(x=10, y=10)
        self.bat_label.place(x=10, y=30)
        self.adc_label.place(x=10, y=50)
        self.rtc_label.place(x=10, y=70)
        self.intrtc_label.place(x=10, y=90)
        self.ntp_label.place(x=10, y=110)
        self.update_status_but.place(x=10, y=130)
        self.helios_canvas.place(x=150, y=10)
        self.sol_control.place(x=1110, y=10)
        self.abs_control.place(x=1110, y=30)
        self.add_pt_but.place(x=1110, y=70)
        self.save_scene_but.place(x=1110, y=110)
        self.test_scene_but.place(x=1110, y=150)
        self.clean_scene_but.place(x=1110, y=190)
        self.load_scene_but.place(x=1110, y=230)
        
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
        self.helios_canvas.create_circle(self.a2c(self.my_helios.alt_setpoint, self.my_helios.azi_setpoint), 10,  fill="#BBB", outline="")
        sun_azi, sun_alt = get_sun_position((self.my_helios.lon, self.my_helios.lat), datetime.datetime.now(datetime.timezone.utc).isoformat()[:-6]) 
        self.helios_canvas.create_circle(self.a2c(sun_alt, sun_azi), 20, fill='yellow', outline='orange')
        #ref = get_reflected_point(self.my_helios)
        #self.helios_canvas.create_circle(self.a2c(ref[0], ref[1]), 10, fill='yellow', outline='blue')

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


    

class HeliosGUI():
    def __init__(self):
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
        self.control_mode = 'absolute'

        self.draw_main_space()

        self.window.after(1000, self.send_motor_cmd)
        self.window.after(10, self.update)

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
            h_idx = self.main_tab.index(self.main_tab.select())
            h = self.helios[h_idx]
            h.azi_setpoint += 2.0
            if h.azi_setpoint > 360.:
                h.azi_setpoint -= 360.
            self.update_position = True


    def left_arrow(self, event):
        if len(self.helios) == 0:
            return
        else:
            h_idx = self.main_tab.index(self.main_tab.select())
            h = self.helios[h_idx]
            h.azi_setpoint -= 2.0
            if h.azi_setpoint < 0:
                h.azi_setpoint += 360.
            self.update_position = True

    def down_arrow(self, event):
        if len(self.helios) == 0:
            return
        else:
            speed = 2
            h_idx = self.main_tab.index(self.main_tab.select())
            h = self.helios[h_idx]
            h.alt_setpoint -= speed
            if h.alt_setpoint < 0.:
                h.alt_setpoint += 360.
            if h.alt_setpoint < 270 and h.alt_setpoint >= 180:
                h.alt_setpoint = 270
            self.update_position = True

    def up_arrow(self, event):
        if len(self.helios) == 0:
            return
        else:
            speed = 2
            h_idx = self.main_tab.index(self.main_tab.select())
            h = self.helios[h_idx]
            h.alt_setpoint += speed
            if h.alt_setpoint > 360.:
                h.alt_setpoint -= 360

            if h.alt_setpoint > 90.0 and h.alt_setpoint < 180:
                h.alt_setpoint = 90.
            self.update_position = True

    def update(self):
        if len(self.helios) == 0:
            pass
        else:
            h_idx = self.main_tab.index(self.main_tab.select())
            h = self.helios[h_idx]
            self.helios_tabs[h_idx].update()
            
        self.window.after(10, self.update)

    def send_motor_cmd(self):
        if self.update_position:
            h_idx = self.main_tab.index(self.main_tab.select())
            h = self.helios[h_idx]
            thr = threading.Thread(target=h.absolute_move, args=(h.alt_setpoint, h.azi_setpoint))
            thr.start() 
        self.window.after(250, self.send_motor_cmd)


    def main_loop(self):
        self.window.mainloop()

    def quit(self):
        self.window.destroy()

if __name__ == "__main__":
    hgui = HeliosGUI()
    hgui.main_loop()


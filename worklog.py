# coding=utf-8
import gi
import threading
import os
import datetime

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from os.path import expanduser

STOPPED_ICON = "stop"
STARTED_ICON = "applications-development"


STORAGE_DIR = ".devworklog"
PROBE_SLEEP = 2

home = expanduser("~")
storage_path = "/".join((home, STORAGE_DIR))


class Indicator:
    def __init__(self, toggle_callback, quit_callback):
        self.status_icon = Gtk.StatusIcon()
        self.status_icon.set_from_icon_name(STOPPED_ICON)

        self.menu = Gtk.Menu()

        self.toggle_btn = Gtk.MenuItem()
        self.toggle_btn.set_label("Start")
        self.toggle_btn.connect("activate", toggle_callback)

        self.menu.append(self.toggle_btn)

        quit_btn = Gtk.MenuItem()
        quit_btn.set_label("Quit")
        quit_btn.connect("activate", quit_callback)
        self.menu.append(quit_btn)

        self.menu.show_all()
        self.status_icon.connect("button-press-event", self.on_click)

    def stop(self):
        self.toggle_btn.set_label("Start")
        self.status_icon.set_from_icon_name(STOPPED_ICON)

    def start(self):
        self.toggle_btn.set_label("Stop")
        self.status_icon.set_from_icon_name(STARTED_ICON)

    def set_tooltip_text(self, text):
        self.status_icon.set_tooltip_text(text)

    def on_click(self, data, event):
        self.menu.popup(None, None, None, self.status_icon, event.button, Gtk.get_current_event_time())


class Worklogger:
    def __init__(self):
        self.running = False
        self.timer = None
        self.poke = None
        self.update_timing_lock = threading.Lock()

        self.indicator = Indicator(self.toggle, self.quit)
        self.indicator.set_tooltip_text(self.howlong())

        ask_to_start = DialogWindow(self)
        ask_to_start.show_all()

    def quit(self, widget):
        if self.running:
            self.running = False
            self.update_timing()
        Gtk.main_quit()

    def toggle(self, widget):
        self.running = not self.running
        self.update_timing()

    def start(self):
        self.running = True
        self.update_timing()

    def update_timing(self):
        self.update_timing_lock.acquire()
        if self.running:
            self.indicator.start()
            self.start_timer()
        else:
            self.indicator.stop()
            self.stop_timer()
        self.update_timing_lock.release()

    def start_timer(self):
        self.timer = threading.Thread(target=self.timer_proc)
        self.timer.start()

    def stop_timer(self):
        # TODO this if can be avoided by provisioning timer thread
        if self.poke is not None:
            self.poke.set()
        self.timer.join()

    def timer_proc(self):
        self.poke = threading.Event()
        while self.running:
            self.poke.wait(PROBE_SLEEP)
            self.logwork()
            self.indicator.set_tooltip_text(self.howlong())

    def logwork(self):
        now = datetime.datetime.now()
        month_dir = self.get_month_dir(now)
        directory = os.path.dirname(month_dir)
        if not os.path.exists(directory):
            os.makedirs(directory)

        day_file = open(month_dir + str(now.day), mode='a+', buffering=0)
        day_file.write(now.strftime("%H:%M\n"))
        day_file.close()

    def howlong(self):
        now = datetime.datetime.now()
        month_dir = self.get_month_dir(now)
        if not os.path.exists(os.path.dirname(month_dir)):
            return "0"

        day_file = open(month_dir + str(now.day), "r")
        lines = set()
        for line in day_file:
            lines.add(line)
        from datetime import timedelta
        return str(timedelta(minutes=len(lines)))[:-3]

    @staticmethod
    def get_month_dir(date):
        return "/".join((storage_path, str(date.year), str(date.month))) + "/"


class DialogExample(Gtk.Dialog):

    def __init__(self, parent):
        Gtk.Dialog.__init__(self, "Kul Worklog", parent, 0,
                            (Gtk.STOCK_NO, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_YES, Gtk.ResponseType.OK))

        self.set_default_size(250, 100)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_urgency_hint(True)
        self.set_keep_above(True)

        label = Gtk.Label("Rozpocząć pracę?")

        box = self.get_content_area()
        box.add(label)
        self.show_all()


class DialogWindow(Gtk.Window):

    def __init__(self, owner):
        Gtk.Window.__init__(self, title="Kul Worklog")

        dialog = DialogExample(self)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            owner.start()

        dialog.destroy()
        self.destroy()


def main():
    Gtk.main()
    return 0


if __name__ == "__main__":
    indicator = Worklogger()
    main()

import tkinter as tk
from tkinter import messagebox
import threading
import automator


class Application:

    def __init__(self):
        self.root = tk.Tk()
        self.running = False
        self.auto = automator.Automator()
        self.scene = LoginScene(self.root, self.auto, self.change_scene)

    def mainloop(self):
        self.root.mainloop()

    def reset_scene(self, new_scene, args=(), kwargs=None):
        if kwargs is None:
            kwargs = {}

        for widget in self.root.winfo_children():
            widget.destroy()
        self.scene = new_scene(*args, **kwargs)

    def change_scene(self, current_scene, going_forward, *args, **kwargs):
        if isinstance(current_scene, LoginScene):
            self.reset_scene(ActivitySelectScene, args=(self.root, self.auto, self.change_scene))
        if isinstance(current_scene, ActivitySelectScene):
            self.reset_scene(OptionsScene, args=(self.root, self.auto, self.change_scene))
        if isinstance(current_scene, OptionsScene):
            if going_forward:
                self.reset_scene(RunningScene, args=(self.root,
                                                     self.auto,
                                                     self.change_scene))
            else:
                pass  # Go back to activity select scene
        if isinstance(current_scene, RunningScene):
            if going_forward:
                pass  # go back to activities, clear all data necessary using auto.clear() or something
            else:
                pass  # go back to options


class LoginScene:
    def __init__(self, root, auto, change_scene):
        self.root = root
        self.auto = auto
        self.change_scene = change_scene

        self.thread = None

        self.root.geometry("300x190+0+10")
        self.root.resizable(False, False)
        self.root.title("Auto-Conjuguemos")
        self.root.bind("<Return>", self.login)

        self.default_font = ("Helvetica", 12)

        tk.Label(self.root, text="Conjuguemos Login Info", font=("Helvetica", 14), relief='groove'
                 ).pack(pady=5, ipady=3, fill='x')

        tk.Label(self.root, text="Username:", font=self.default_font, anchor='w').pack(fill='x', padx=10, pady=1)
        self.username_entry = tk.Entry(self.root, font=self.default_font)
        self.username_entry.pack(fill='x', padx=10, pady=1, ipady=1)
        tk.Label(self.root, text="Password:", font=self.default_font, anchor='w').pack(fill='x', padx=10, pady=1)
        self.password_entry = tk.Entry(self.root, font=("Helvetica", 10), show="*")
        self.password_entry.pack(fill='x', padx=10, pady=1, ipady=1)

        with open("res/saved_login.txt", 'r') as f:
            login_lines = f.readlines()
            for i in range(len(login_lines)):
                login_lines[i] = login_lines[i].replace("\n", "")

        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill='both', expand=1)

        self.remember_login = tk.IntVar(0)
        tk.Checkbutton(bottom_frame, text="Remember Login", font=self.default_font, var=self.remember_login
                       ).pack(side='left', padx=10)

        if len(login_lines) > 1:
            self.username_entry.insert('end', login_lines[0])
            self.password_entry.insert('end', login_lines[1])
            self.remember_login.set(1)

        self.login_button = tk.Button(bottom_frame, text='Login', font=('Helvetica', 13), bg='gray85',
                                      command=self.login)
        self.login_button.pack(side='right', ipadx=6, padx=10)

    def login(self, *args):
        if self.password_entry.get() == "" or self.username_entry.get() == "":
            messagebox.showinfo("Warning!", "The username or password can not be empty!")
        else:
            if self.thread is None:
                self.thread = threading.Thread(target=self.auto.login, args=(self.username_entry.get(),
                                                                             self.password_entry.get(),
                                                                             self.login_result,
                                                                             self.login_unsuccessful))
                self.thread.start()

    def save_login(self, username, password):
        with open("res/saved_login.txt", 'w') as f:
            if self.remember_login.get():
                f.write(username + '\n' + password)

    def login_result(self, username, password, result):
        if result:
            self.save_login(username, password)
            self.change_scene(self, True);
        else:
            messagebox.showinfo("Warning!", "Username or password not accepted. Try again.")

        self.thread = None

    @staticmethod
    def login_unsuccessful():
        messagebox.showinfo("Warning!", "Login attempt timed out. Try again.")


class ActivitySelectScene:
    def __init__(self, root, auto, change_scene):
        self.root = root
        self.auto = auto
        self.root.geometry("450x450")
        self.root.resizable(False, False)
        self.root.title("Auto-Conjuguemos")

        self.change_scene = change_scene

        self.thread = None

        self.default_font = ("Helvetica", 12)

        self.bottom_strip = tk.Frame(self.root)
        self.bottom_strip.pack(side='bottom', fill='x')

        tk.Label(self.root, text="Select an Activity:", font=("Helvetica", 16), anchor='w').pack(fill='x', padx=10,
                                                                                                 pady=5)
        self.listbox = tk.Listbox(self.root, font=self.default_font)
        self.listbox.pack(expand=1, fill='both', padx=10)

        self.activity_list = self.auto.get_activities()
        for i, activity in enumerate(self.activity_list):
            self.listbox.insert(i, f"{i + 1}. {activity['name']}")

        self.scrollbar = tk.Scrollbar(self.listbox)
        self.scrollbar.pack(side='right', fill='y')
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.config(yscrollcommand=self.scrollbar.set)

        tk.Button(self.bottom_strip, text="Continue", font=("Helvetica", 16), bg='gray85', command=self.select_scene
                  ).pack(side='right', padx=10, pady=5)

    def select_scene(self):
        if self.thread is None:
            try:
                self.listbox.curselection()[0]
            except IndexError:
                return

            tk.Label(self.bottom_strip, text="Loading Activity...", font=("Helvetica", 16), relief='groove', bg='gray90'
                     ).pack(side='left', padx=10, pady=5)
            self.root.update()

            self.thread = threading.Thread(target=self.load_scene,
                                           args=(self.activity_list[self.listbox.curselection()[0]],))
            self.thread.start()

    def load_scene(self, activity):
        activity['click']()  # clicks activity
        self.auto.get_data(activity['name'])
        self.change_scene(self, True)


class LabelEntry:
    def __init__(self, frame, row, label_text, entry_width, max_entry_char, val, val_endstr=""):
        self.val_endstr = val_endstr

        self.max_entry_char = max_entry_char

        self.text = tk.StringVar()
        self.text.trace('w', self.on_write)
        tk.Label(frame, text=label_text, anchor='e', font=("Helvetica", 14)
                 ).grid(column=0, sticky='e', row=row, padx=10, pady=5)
        self.entry = tk.Entry(frame, width=entry_width, textvariable=self.text, font=("Helvetica", 14))
        self.entry.grid(column=1, row=row, sticky='w', pady=5, padx=(2, 0))
        self.entry.insert('end', val)

    def on_write(self, *args):
        s = self.text.get()
        if len(s) > self.max_entry_char:
            self.text.set(s[:self.max_entry_char])


class OptionsScene:
    def __init__(self, root, auto, change_scene):
        self.root = root
        self.root.geometry("450x450")
        self.root.resizable(False, False)
        self.auto = auto
        self.change_scene = change_scene

        tk.Label(self.root, text="Current Activity:", font=("Helvetica", 16, 'bold'), relief='groove',
                 ).pack(fill='x', ipady=2)
        tk.Label(self.root, text=self.auto.activity_auto.name, font=("Helvetica", 14), relief='groove',
                 ).pack(fill='x', pady=(0, 30))

        option_frame = tk.Frame()
        option_frame.pack(fill='x')
        option_frame.columnconfigure(0, weight=1)
        option_frame.columnconfigure(1, weight=2)
        option_frame.rowconfigure(3, weight=0)

        leftentry_width = 4
        max_entry_char = 3

        self.timer = LabelEntry(option_frame, 0, "Timer (minutes):", leftentry_width, max_entry_char,
                                10)
        self.word_amount = LabelEntry(option_frame, 1, "Amount of Words:", leftentry_width, max_entry_char,
                                      100)
        self.percent = LabelEntry(option_frame, 2, "Target Percent:", leftentry_width, 4,
                                  100, '%')
        self.speed = LabelEntry(option_frame, 3, "Seconds per Word:", leftentry_width, 4,
                                0.01, ' s')
        self.auto_submit = tk.IntVar()
        self.auto_submit.set(0)
        tk.Checkbutton(option_frame, text="Automatically Submit", font=("Helvetica", 14), var=self.auto_submit
                       ).grid(row=4, column=0, columnspan=2, pady=(30, 5))

        buttons = tk.Frame(self.root)
        buttons.pack(side='bottom', fill='x', padx=10, pady=10)
        tk.Button(buttons, text="Back", font=("Helvetica", 14), bg='gray90',
                  command=lambda: self.change_scene(self, False)
                  ).pack(side='left')
        tk.Button(buttons, text="Continue", font=("Helvetica", 14), bg='gray90', command=self.set_values
                  ).pack(side='right')

    def set_values(self):
        time_limit = self.timer.entry.get().replace("m", "").strip()

        word_amount = self.word_amount.entry.get()

        target_percent = self.percent.entry.get().replace("%", "").strip()

        speed = self.speed.entry.get().replace("s", "").strip()

        if not time_limit.isnumeric():
            messagebox.showinfo("Warning!", "The timer value is not acceptable. It must not have a decimal.")
            return

        if not word_amount.isnumeric():
            messagebox.showinfo("Warning!", "The word amount value is not acceptable. It must not have a decimal.")
            return

        if not target_percent.isnumeric():
            messagebox.showinfo("Warning!", "The target percent value is not acceptable. It must not have a decimal.")
            return

        try:
            float(speed)
        except ValueError:
            messagebox.showinfo("Warning!", "The seconds per word value is not acceptable.")
            return

        self.auto.activity_auto.set_options(
            time_limit=min(45, max(1, int(time_limit))),
            word_amount=min(499, max(0, int(word_amount))),
            target_percent=min(100, max(0, int(target_percent))),
            speed=max(0.01, float(speed)),
            auto_submit=self.auto_submit.get())

        self.change_scene(self, True)


class LabelDisplay:
    def __init__(self, frame, row, label_text, value_width, data=None):
        self.text = tk.StringVar()
        tk.Label(frame, text=label_text, anchor='e', font=("Helvetica", 14)
                 ).grid(column=0, sticky='e', row=row, padx=10, pady=5)
        self.data = tk.Label(frame, width=value_width, font=("Helvetica", 14), text=data, relief='groove')
        self.data.grid(column=1, row=row, sticky='w', pady=5, padx=(2, 0))

    def update_data(self, new_text):
        self.data.config(text=new_text)


class RunningScene:
    def __init__(self, root, auto, change_scene):
        self.root = root
        self.root.geometry("450x450")
        self.root.resizable(False, False)
        self.auto = auto
        self.change_scene = change_scene

        self.auto.prepare_start()

        self.thread = threading.Thread(target=self.auto.activity_auto.run_automation,
                                       args=(self.update,
                                             RunningScene.failed))
        self.thread.start()

        tk.Label(self.root, text="Current Activity:", font=("Helvetica", 16, 'bold'), relief='groove',
                 ).pack(fill='x', ipady=2)
        tk.Label(self.root, text=self.auto.activity_auto.name, font=("Helvetica", 14), relief='groove',
                 ).pack(fill='x', pady=(0, 30))

        option_frame = tk.Frame()
        option_frame.pack(fill='both')
        option_frame.columnconfigure(0, weight=1)
        option_frame.columnconfigure(1, weight=2)

        value_width = 8

        LabelDisplay(option_frame, 0, "Duration:", value_width, data=str(self.auto.activity_auto.time_limit) + " min")

        self.current_time_ld = LabelDisplay(option_frame, 0, "Time Left:",
                                            value_width, data=str(self.auto.activity_auto.time_limit)+":00")

        LabelDisplay(option_frame, 1, "Amount of Words:",
                     value_width, data=self.auto.activity_auto.word_amount)

        self.current_words_ld = LabelDisplay(option_frame, 2, "Current Words:", value_width, data="0")

        self.current_percent_ld = LabelDisplay(option_frame, 3, "Current Percent:", value_width, data="-")

        LabelDisplay(option_frame, 4, "Target Percent:",
                     value_width, data=str(self.auto.activity_auto.target_percent) + "%")

        LabelDisplay(option_frame, 5, "Seconds per Word:",
                     value_width, data=str(self.auto.activity_auto.speed) + " s")

        LabelDisplay(option_frame, 6, "Auto Submitting:",
                     value_width, data="Yes" if self.auto.activity_auto.auto_submit else "No")

    def update(self, current_secs, current_mins, current_words, current_percent):
        self.current_time_ld.update_data(str(current_mins) + ":" + (str(current_secs) if current_secs != 0 else "00"))
        self.current_words_ld.update_data(current_words)
        self.current_percent_ld.update_data(str(current_percent)+"%")

    @staticmethod
    def failed():
        messagebox.showinfo("Error!", "There was an error. Please restart the app...")

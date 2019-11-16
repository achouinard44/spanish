"""Controls the flow of the Auto-Conjuguemos GUI application.

This module controls the GUI and gives an Automator instance instructions based
on values entered by the user in the GUI. The Application class stores the
tkinter root and Automator instance. There are multiple Scene classes that can
occupy the Application's current scene attribute. Each scene makes use of the
main Application's tkinter root and Automator instance to control the GUI and
conjuguemos automation.

The Application can be instantiated without arguments:

>>> app = Application()

The mainloop method starts and runs the application.

>>> app.mainloop()

"""

import threading
import tkinter as tk
from tkinter import messagebox

from cryptography.fernet import Fernet

import automator


class Application:
    """The main application class for Auto-Conjuguemos.

    Attributes:
        root: The tkinter GUI root.
        auto: The Automator instance that runs the webdriver.
        scene: The current scene that the GUI is displaying.
    """

    def __init__(self):
        self.root = tk.Tk()
        self.auto = automator.Automator()
        self.scene = LoginScene(self.root, self.auto, self.change_scene)
 
    def mainloop(self):
        self.root.mainloop()

    def swap_scene(self, new_scene, args=(), kwargs=None):
        """Clears the current Scene and switches to a new Scene.

        Args:
            new_scene: Scene class to switch to.
        Kwargs:
            args: Arguments to instantiate new_scene class with.
            kwargs: Keyword arguments to instantiate new_scene class with.
        """

        if kwargs is None:
            kwargs = {}

        for widget in self.root.winfo_children():
            widget.destroy()
        self.scene = new_scene(*args, **kwargs)

    def change_scene(self, current_scene, going_forward):
        """Switches to the next or previous scene in the application.

        Args:
            current_scene: The current Scene class.
            going_foward: True if going forward in scene progression.
        """

        if isinstance(current_scene, LoginScene):
            self.swap_scene(ActivitySelectScene, args=(
                self.root, self.auto, self.change_scene))

        elif isinstance(current_scene, ActivitySelectScene):
            if going_forward:
                self.swap_scene(OptionsScene,
                                 args=(self.root, self.auto, self.change_scene))
            else:
                self.swap_scene(LoginScene,
                                 args=(self.root, self.auto, self.change_scene))

        elif isinstance(current_scene, OptionsScene):
            if going_forward:
                self.swap_scene(AutomationScene, args=(self.root,
                                                     self.auto,
                                                     self.change_scene))
            else:
                self.swap_scene(ActivitySelectScene,
                                 args=(self.root, self.auto, self.change_scene))

        elif isinstance(current_scene, AutomationScene):
            if going_forward:
                self.swap_scene(ActivitySelectScene, args=(
                    self.root, self.auto, self.change_scene))
            else:
                self.swap_scene(OptionsScene,
                                 args=(self.root, self.auto, self.change_scene))


class LoginScene:
    """The scene where the user enters their login information for 
    conjuguemos.
    
    Args:
        root: The tkinter window root.
        auto: The Automator class instance used by the application.
        change_scene: Function used to move forward or backward a scene.
    """

    def __init__(self, root, auto, change_scene):

        self.root = root
        self.auto = auto
        self.change_scene = change_scene

        self.root.geometry("300x190+0+10")
        self.root.resizable(False, False)
        self.root.title("Auto-Conjuguemos")
        self.root.bind("<Return>", self.login)

        self.thread = None

        ########################################################################
        # GUI Style and Structure:
        ########################################################################

        self.default_font = ("Helvetica", 12)

        tk.Label(self.root, text="Conjuguemos Login Info", 
                 font=("Helvetica", 14), relief='groove'
                 ).pack(pady=5, ipady=3, fill='x')

        tk.Label(self.root, text="Username:", font=self.default_font,
                 anchor='w').pack(fill='x', padx=10, pady=1)
        self.username_entry = tk.Entry(self.root, font=self.default_font)
        self.username_entry.pack(fill='x', padx=10, pady=1, ipady=1)

        tk.Label(self.root, text="Password:", font=self.default_font,
                 anchor='w').pack(fill='x', padx=10, pady=1)
        self.password_entry = tk.Entry(
            self.root, font=("Helvetica", 10), show="*")
        self.password_entry.pack(fill='x', padx=10, pady=1, ipady=1)

        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill='both', expand=1)

        self.remember_login = tk.IntVar(0)
        tk.Checkbutton(bottom_frame, text="Remember Login", 
                       font=self.default_font, var=self.remember_login
                       ).pack(side='left', padx=10)

        self.login_button = tk.Button(bottom_frame, text='Login', 
            font=('Helvetica', 13), bg='gray85', command=self.login)

        self.login_button.pack(side='right', ipadx=6, padx=10)

        self.fill_saved_login()

    def fill_saved_login(self):
        """Auto-fills the login boxes if there is a saved login."""

        with open("res/saved_login.txt", 'r') as f:
            login_lines = f.readlines()
            for i in range(len(login_lines)):
                login_lines[i] = login_lines[i].replace("\n", "")

        if len(login_lines) > 1:
            key = str.encode(login_lines[0])
            cipher_suite = Fernet(key)
            decoded_pass = cipher_suite.decrypt(str.encode(login_lines[2])).decode()

            self.username_entry.insert('end', login_lines[1])
            self.password_entry.insert('end', decoded_pass)
            self.remember_login.set(1)

    def login(self, *args):
        """Sends a thread that attempts to log into conjuguemos."""

        if self.password_entry.get() == "" or self.username_entry.get() == "":
            messagebox.showinfo(
                "Warning!", "The username or password can not be empty!")
        elif self.thread is None:

            def try_login():
                username = self.username_entry.get()
                password = self.password_entry.get()
                result = self.auto.login(username, password)
                if result is True:
                    self.save_login(username, password)
                    self.change_scene(self, True)
                elif result is False:
                    messagebox.showinfo(
                        "Warning!", 
                        "Username or password not accepted. Try again.")
                else:
                    self.login_unsuccessful()

                self.thread = None

            self.thread = threading.Thread(target=try_login) 
            self.thread.start()

    def save_login(self, username, password):
        """Saves login info to a file."""

        with open("res/saved_login.txt", 'w') as f:
            if self.remember_login.get():
                key = Fernet.generate_key().decode()
                cipher_suite = Fernet(key)
                encoded_pass = cipher_suite.encrypt(str.encode(password)).decode()
                f.write(key + '\n' + username + '\n' + encoded_pass)

    @staticmethod
    def login_unsuccessful():
        messagebox.showinfo("Warning!", "Login attempt timed out. Try again.")


class ActivitySelectScene:
    """The scene where the user chooses a conjuguemos activity to complete.
    
    Args:
        root: The tkinter window root.
        auto: The Automator class instance used by the application.
        change_scene: Function used to move forward or backward a scene.
    """

    def __init__(self, root, auto, change_scene):

        self.root = root
        self.auto = auto
        self.root.geometry("450x450")
        self.root.resizable(False, False)
        self.root.title("Auto-Conjuguemos")

        self.change_scene = change_scene

        self.thread = None

        ########################################################################
        # GUI Style and Structure:
        ########################################################################

        self.default_font = ("Helvetica", 12)

        bottom_strip = tk.Frame(self.root)
        bottom_strip.pack(side='bottom', fill='x')

        self.top_strip = tk.Frame(self.root)
        self.top_strip.pack(side='top', fill='x')

        tk.Label(self.top_strip, text="Select an Activity:", 
                 font=("Helvetica", 16), anchor='w'
                 ).pack(side='left', padx=10, pady=5)
        
        self.listbox = tk.Listbox(self.root, font=self.default_font)
        self.listbox.pack(expand=1, fill='both', padx=10)

        self.activity_list = self.auto.get_activities()
        for i, activity in enumerate(self.activity_list):
            self.listbox.insert(i, f"{i + 1}. {activity['name']}")

        self.scrollbar = tk.Scrollbar(self.listbox)
        self.scrollbar.pack(side='right', fill='y')
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.config(yscrollcommand=self.scrollbar.set)

        tk.Button(bottom_strip, text="Continue",
                  font=("Helvetica", 16), bg='gray85', command=self.select_scene
                  ).pack(side='right', padx=10, pady=5)

        tk.Button(bottom_strip, text="Back to Login",
                  font=("Helvetica", 16), bg='gray85', command=self.go_back
                  ).pack(side='left', padx=10, pady=5)

    def select_scene(self):
        """Starts the loading process for the currently selected scene."""

        if self.thread is not None:
            return

        try:
            self.listbox.curselection()[0]
        except IndexError:
            return

        tk.Label(self.top_strip, text="Loading Activity...",
                    font=("Helvetica", 16), relief='groove', bg='gray90'
                    ).pack(side='right', padx=10, pady=5)
        self.root.update()

        def load_and_switch():
            
            activity = self.activity_list[self.listbox.curselection()[0]]

            activity['click']()  # clicks activity

            self.auto.get_data(activity['name'])

            self.change_scene(self, True)

        self.thread = threading.Thread(target=load_and_switch)
        self.thread.start()

    def go_back(self):
        """Goes back to the login page."""

        self.auto.login_page()

        self.change_scene(self, False)


class LabelEntry:
    """Wrapper class for a widget that takes an entry input.

    Stores a value self.text can can be changed using the entry element.
    The label can have description text.

    Args:
        frame: The tkinter frame.
        row: The row to put the LabelEntry in.
        label_text: String text for the label.
        entry_width: The width of the entry element.
        max_entry_char: Maximum amount of input characters to accept.
        val: Default value for the input field.
    Kwargs:
        val_endstr: The string to add to the end of the displayed value.
    """

    def __init__(self, frame, row, label_text, entry_width, 
                 max_entry_char, val, val_endstr=""):

        self.val_endstr = val_endstr

        self.max_entry_char = max_entry_char

        self.text = tk.StringVar()
        self.text.trace('w', self.on_write)
        tk.Label(frame, text=label_text, anchor='e', font=("Helvetica", 14)
                 ).grid(column=0, sticky='e', row=row, padx=10, pady=5)
        self.entry = tk.Entry(frame, width=entry_width,
                              textvariable=self.text, font=("Helvetica", 14))
        self.entry.grid(column=1, row=row, sticky='w', pady=5, padx=(2, 0))
        self.entry.insert('end', val)

    def on_write(self, *args):
        """Constrains the entry input to a max amount self.max_entry_char."""

        s = self.text.get()
        if len(s) > self.max_entry_char:
            self.text.set(s[:self.max_entry_char])


class OptionsScene:
    """Scene where the options for the automation are chosen.

    Target percent, word amount, time, etc, are all chosen in this Scene.

    Args:
        root: The tkinter root.
        auto: The application's shared Automator instance.
        change_scene: Function to change to next or previous scene.
    """

    def __init__(self, root, auto, change_scene):

        self.root = root
        self.root.geometry("450x450")
        self.root.resizable(False, False)
        self.auto = auto
        self.change_scene = change_scene

        self.loading = False

        ########################################################################
        # GUI Style and Structure:
        ########################################################################

        tk.Label(self.root, text="Current Activity:",
                 font=("Helvetica", 16, 'bold'), relief='groove',
                 ).pack(fill='x', ipady=2)
        tk.Label(self.root, text=self.auto.activity_auto.name,
                 font=("Helvetica", 14), relief='groove',
                 ).pack(fill='x', pady=(0, 30))

        option_frame = tk.Frame()
        option_frame.pack(fill='x')
        option_frame.columnconfigure(0, weight=1)
        option_frame.columnconfigure(1, weight=2)
        option_frame.rowconfigure(3, weight=0)

        leftentry_width = 4
        max_entry_char = 3

        self.timer = LabelEntry(option_frame, 0, "Timer (minutes):",
                                leftentry_width, max_entry_char, 10)

        self.word_amount = LabelEntry(option_frame, 1, "Word Target:",
                                      leftentry_width, max_entry_char, 100)

        self.percent = LabelEntry(option_frame, 2, "Target Percent:",
                                  leftentry_width, 4, 100, '%')

        self.speed = LabelEntry(option_frame, 3, "Seconds per Word:",
                                leftentry_width, 4, 0.01, ' s')

        self.auto_submit = tk.IntVar()
        self.auto_submit.set(0)

        tk.Checkbutton(option_frame, text="Automatically Submit",
                       font=("Helvetica", 14), var=self.auto_submit
                       ).grid(row=4, column=0, columnspan=2, pady=(30, 5))

        buttons = tk.Frame(self.root)
        buttons.pack(side='bottom', fill='x', padx=10, pady=10)

        tk.Button(buttons, text="Back", font=("Helvetica", 14), bg='gray90',
                  command=self.go_back
                  ).pack(side='left')
        tk.Button(buttons, text="Continue", font=("Helvetica", 14),
                  bg='gray90', command=self.enter_values
                  ).pack(side='right')

    def enter_values(self):
        """Enters all values and switches to next scene."""

        if self.loading:
            return

        time_limit = self.timer.entry.get().replace("m", "").strip()

        word_amount = self.word_amount.entry.get()

        target_percent = self.percent.entry.get().replace("%", "").strip()

        speed = self.speed.entry.get().replace("s", "").strip()

        if not time_limit.isnumeric():
            messagebox.showinfo(
                "Warning!", "The timer value is not acceptable. It must not have a decimal.")
            return

        if not word_amount.isnumeric():
            messagebox.showinfo(
                "Warning!", "The word amount value is not acceptable. It must not have a decimal.")
            return

        if not target_percent.isnumeric():
            messagebox.showinfo(
                "Warning!", "The target percent value is not acceptable. It must not have a decimal.")
            return

        try:
            float(speed)
        except ValueError:
            messagebox.showinfo(
                "Warning!", "The seconds per word value is not acceptable.")
            return

        self.auto.activity_auto.set_options(
            time_limit=min(45, max(1, int(time_limit))),
            word_amount=min(499, max(0, int(word_amount))),
            target_percent=min(100, max(0, int(target_percent))),
            speed=max(0.01, float(speed)),
            auto_submit=self.auto_submit.get())

        def prep_and_change_scene():
            self.auto.prepare_start()
            self.change_scene(self, True)

        threading.Thread(target=prep_and_change_scene).start()

        self.loading = True

    def go_back(self):
        """Goes back to the previous scene."""

        if self.loading:
            return

        self.auto.driver.back()

        self.change_scene(self, going_forward=False)


class LabelDisplay:
    """Displays a label with a value that can be constantly updated.
    
    Args:
        frame: The tkinter frame to put the LabelDisplay in.
        row: The row in the frame to put the LabelDisplay in.
        label_text: The string to put on the label.
        value_width: The width of the value display slot.
    Kwargs:
        data: The initial text to put in the data display.
    """

    def __init__(self, frame, row, label_text, value_width, data=None):
        self.text = tk.StringVar()
        tk.Label(frame, text=label_text, anchor='e', font=("Helvetica", 14)
                 ).grid(column=0, sticky='e', row=row, padx=10, pady=5)
        self.data = tk.Label(frame, width=value_width, font=(
            "Helvetica", 14), text=data, relief='groove')
        self.data.grid(column=1, row=row, sticky='w', pady=5, padx=(2, 0))

    def update_data(self, new_text):
        """Updates the data with new_text."""

        self.data.config(text=new_text)


class AutomationScene:
    """The Scene that is displayed during the automation phase.
    
    Args:
        root: The tkinter root.
        auto: The Automator instance used to control the webdriver.
        change_scene: Function that controls the application's scene flow.
    """

    def __init__(self, root, auto, change_scene):
        self.root = root
        self.root.geometry("450x450")
        self.root.resizable(False, False)
        self.auto = auto
        self.change_scene = change_scene

        # Starts the automation loop in a separate thread
        def auto_func():
            if not self.auto.activity_auto.run_automation(self.update):
                AutomationScene.failed()
            self.finished()

        self.thread = threading.Thread(target=auto_func)
        self.thread.start()

        ########################################################################
        # GUI Style and Structure:
        ########################################################################

        tk.Label(self.root, text="Current Activity:",
                 font=("Helvetica", 16, 'bold'), relief='groove',
                 ).pack(fill='x', ipady=2)
        tk.Label(self.root, text=self.auto.activity_auto.name,
                 font=("Helvetica", 14), relief='groove',
                 ).pack(fill='x', pady=(0, 30))

        option_frame = tk.Frame()
        option_frame.pack(fill='both')
        option_frame.columnconfigure(0, weight=1)
        option_frame.columnconfigure(1, weight=2)

        value_width = 8

        LabelDisplay(option_frame, 0, "Duration:", value_width,
                     data=str(self.auto.options["time_limit"]) + " min")

        self.current_time_ld = LabelDisplay(
            option_frame, 0, "Time Left:", value_width,
            data=str(self.auto.options["time_limit"])+":00")

        self.current_words_ld = LabelDisplay(
            option_frame, 2, "Current Words:", value_width, 
            data=f"0/0")

        LabelDisplay(option_frame, 3, "Word Target:", value_width,
                     data=self.auto.options["word_amount"])

        self.current_percent_ld = LabelDisplay(
            option_frame, 4, "Current Percent:", value_width, data="-")

        LabelDisplay(option_frame, 5, "Target Percent:",
                     value_width,
                     data=str(self.auto.options["target_percent"]) + "%")

        LabelDisplay(option_frame, 6, "Seconds per Word:",
                     value_width,
                     data=str(self.auto.options["speed"]) + " s")

        LabelDisplay(option_frame, 7, "Auto Submitting:",
                     value_width, data="Yes"
                     if self.auto.options["auto_submit"] else "No")
        
        buttons = tk.Frame(self.root)
        buttons.pack(side='bottom', fill='x', padx=10, pady=10)

        tk.Button(buttons, text="Back", font=("Helvetica", 14), bg='gray90',
                  command=self.go_back
                  ).pack(side='left')
        
        self.complete_button = tk.Button(buttons, text="Complete", 
                  font=("Helvetica", 14), bg='gray90', 
                  command=self.to_activities, state=tk.DISABLED)
        self.complete_button.pack(side='right')

    def update(self, current_secs, current_mins,
               current_words, correct_words, current_percent):
        """Updates the GUI labels with the current values of the automation.

        Args:
            current_secs: Seconds on the ellapsed time clock.
            current_mins: Minutes on the ellapsed time clock.
            current_words: Current amount of words completed.
            correct_words: Current correct amount of words completed.
            current_percent: Current percentage correct.
        """

        self.current_time_ld.update_data(
            str(current_mins) + ":" + 
            (str(current_secs) if current_secs > 9 else f"0{current_secs}"))

        self.current_words_ld.update_data(f"{correct_words}/{current_words}")
        self.current_percent_ld.update_data(str(current_percent)+"%")

    def finished(self):
        """Unlocks the Complete button after the automation is finished."""

        self.complete_button.config(state=tk.NORMAL)

    def go_back(self):
        """Goes back to the previous scene."""

        self.auto.driver.back()
        self.change_scene(self, False)
    
    def to_activities(self):
        """Goes back to activities Scene.
        
        This is run by pressing the Complete button, which can only be pressed
        after the automation is complete.
        """

        if not self.auto.activity_auto.auto_submit:
            response = messagebox.askyesno(
                "Warning! Score not automatically submitted!",
                "You must manually submit your score before you exit this activity! Would you still like to exit?")
            
            if not response:
                return

        self.auto.driver.get("https://conjuguemos.com/student/activities")
        self.change_scene(self, True)

    @staticmethod
    def failed():
        """Called if there is a problem with the automation.

        If there are an error with the automation, this message will be called
        and prompt the user to go back to the last scene and try again.
        """

        messagebox.showinfo(
            "Error!", "There was an error. Please go back and try again.")

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, \
    ElementNotInteractableException
import os
import time

class ActivityOptions:
    def __init__(self):
        self.time_limit = None
        self.word_amount = None
        self.target_percent = None
        self.speed = None
        self.auto_submit = None

    def set_options(self, time_limit=None, word_amount=None, target_percent=None, speed=None, auto_submit=None):
        self.time_limit = time_limit
        self.word_amount = word_amount
        self.target_percent = target_percent
        self.speed = speed
        self.auto_submit = auto_submit


class ActivityAuto(ActivityOptions):
    def __init__(self, driver):
        ActivityOptions.__init__(self)

        self.driver = driver
        self.name = ""
        self.last_action_time = time.time()

        self.button_element = None
        self.answer_element = None
        self.question_index = 0
        self.correct_questions = 0
        self.wrong_questions = 0


class VocabularyAuto(ActivityAuto):
    def __init__(self, driver):
        ActivityAuto.__init__(self, driver)
        self.vocab_dict = {}
        self.question_element = None

    def run_automation(self, update_data, failed):
        try:
            self.question_element = self.driver.find_element_by_id("question-input")
            self.button_element = self.driver.find_element_by_id("check-button")
            self.answer_element = self.driver.find_element_by_id("answer-input")
        except NoSuchElementException:
            failed()
            return

        start_time = time.time()

        while True:
            current_time = time.time()
            elapsed_time = current_time - self.last_action_time

            if self.question_index >= self.word_amount:
                break

            if elapsed_time < self.speed:
                continue

            try:

                self.last_action_time = time.time()

                if self.question_index < self.wrong_questions:
                    ans = f"wrong {self.question_index + 1}"
                else:
                    ans = self.vocab_dict[self.question_element.text]
                    self.correct_questions += 1

                self.answer_element.clear()
                self.answer_element.send_keys(ans)
                self.button_element.click()

                self.question_index += 1

                time_left = 60 * self.time_limit - int(current_time - start_time)
                update_data(time_left % 60,
                            int(time_left / 60),
                            self.question_index,
                            round(100 * self.correct_questions / self.question_index))

            except ElementClickInterceptedException:
                continue



        return True

    def load_data(self):
        table = self.driver.find_element_by_xpath("//table[@class='table table--fat']")
        cells = table.find_elements_by_xpath(".//td")
        english = []
        spanish = []
        self.vocab_dict = {}
        for i, cell in enumerate(cells):
            text = cell.text
            if i % 2 == 0:
                english.append(text[text.find(".") + 1:])
            else:
                spanish.append(text[text.find(".") + 1:])
        for e, s in zip(english, spanish):
            self.vocab_dict[e.strip()] = s.strip()


class ConjugationAuto(ActivityAuto):
    def __init__(self, driver):
        ActivityAuto.__init__(self, driver)
        self.verbs = []
        self.pronoun_element = None
        self.verb_element = None

    def run_automation(self, update_data, failed):
        try:
            self.pronoun_element = self.driver.find_element_by_id("pronoun-input")
            self.verb_element = self.driver.find_element_by_id("verb-input")
            self.button_element = self.driver.find_element_by_id("check-button")
            self.answer_element = self.driver.find_element_by_id("answer-input")
        except NoSuchElementException:
            failed()
            return

        start_time = time.time()

        while True:
            current_time = time.time()
            elapsed_time = current_time - self.last_action_time

            if self.question_index >= self.word_amount:
                break

            if elapsed_time < self.speed:
                continue

            try:

                self.last_action_time = time.time()

                if self.question_index < self.wrong_questions:
                    ans = f"wrong {self.question_index + 1}"
                else:
                    verb = None
                    for verb in self.verbs:
                        if verb['verb'] == self.verb_element.text:
                            break
                    ans = verb[ConjugationAuto.get_pronoun(self.pronoun_element.text)]
                    self.correct_questions += 1

                self.answer_element.clear()
                self.answer_element.send_keys(ans)
                self.button_element.click()

                self.question_index += 1

                time_left = 60*self.time_limit - int(current_time - start_time)
                update_data(time_left % 60,
                            int(time_left / 60),
                            self.question_index,
                            round(100 * self.correct_questions / self.question_index))

            except ElementClickInterceptedException:
                continue

        return True

    def load_data(self):
        table_elements = self.driver.find_elements_by_xpath("//div[@class='mb-60 break']")
        print(table_elements)
        for elem in table_elements:
            verb = elem.find_element_by_class_name("text--up").text.lower()
            pronoun_elements = elem.find_elements_by_xpath(".//td[@class='text-center']")
            pronouns = [pronoun_element.text[:-1] for pronoun_element in pronoun_elements]
            conjugated_elements = elem.find_elements_by_xpath(".//td[@class='text-center fsty--italic']")
            conjugated = [conjugated_element.text for conjugated_element in conjugated_elements]

            verb_dict = {'verb': verb}
            for p, c in zip(pronouns, conjugated):
                verb_dict[p] = c

            self.verbs.append(verb_dict)

    @staticmethod
    def get_pronoun(noun):
        noun = noun.lower()
        if noun in ['yo', 'tú', 'él', 'ella', 'usted', 'nosotros', 'vosotros', 'ellos', 'ellas', 'ustedes']:
            return noun
        elif " y " in noun:
            if " yo" in noun or "yo " in noun:
                return "nosotros"
            else:
                return "ellos"
        else:
            return "él"


class Automator:

    def __init__(self):
        self.driver = webdriver.Firefox(executable_path=os.getcwd() + "\\res\\geckodriver.exe")
        self.driver.maximize_window()
        self.driver.get("https://conjuguemos.com/auth/login")
        self.driver.implicitly_wait(0)

        self.options = None

        self.activity_auto = None

        self.driver.find_element_by_id("identity").send_keys("DO NOT LOGIN HERE! LOGIN IN THE AUTO-CONJUGUEMOS APP")

    @staticmethod
    def loop_for_time(seconds, func, args=(), kwargs=None):
        """
        Continuously loops func for a specified amount of time or until func returns 'done'
        :return False if the func returned False, True if looped for whole duration
        """
        if kwargs is None:
            kwargs = {}

        start = time.time()
        while time.time() - start < seconds:
            if func(*args, **kwargs) == 'done':
                return False
        return True

    def login(self, username, password, result_func, unsuccessful_func):

        username_element = self.driver.find_element_by_id("identity")
        password_element = self.driver.find_element_by_id("password")
        login_element = self.driver.find_element_by_id("login_btn")

        username_element.clear()
        username_element.send_keys(username)
        password_element.clear()
        password_element.send_keys(password)

        login_element.click()

        def looped_func():
            if self.driver.current_url == "https://conjuguemos.com/auth/login":
                try:
                    self.driver.find_element_by_id("form_errors")
                    self.driver.get(self.driver.current_url)
                    result_func(username, password, False)
                    return 'done'
                except NoSuchElementException:
                    pass
            else:
                result_func(username, password, True)
                return 'done'

        if self.loop_for_time(5, looped_func):  # if looped for entire time (didn't log in or fail log in)
            unsuccessful_func()

    def get_activities(self):
        self.driver.implicitly_wait(5)
        activities = self.driver.find_element_by_id("activities")
        activity_element_list = activities.find_elements_by_xpath(".//a")
        self.driver.implicitly_wait(0)
        activity_list = []
        for a in activity_element_list:
            activity_list.append({"name": a.text, "click": a.click})

        return activity_list

    def get_data(self, name):
        if "vocabulary" in self.driver.current_url:
            insertion_pos = self.driver.current_url.find("vocabulary") + len("vocabulary")
            self.driver.get(
                self.driver.current_url[:insertion_pos] + "/vocab_chart" + self.driver.current_url[insertion_pos:])
            self.activity_auto = VocabularyAuto(self.driver)
        else:
            insertion_pos = self.driver.current_url.find("verb") + len("verb")
            self.driver.get(
                self.driver.current_url[:insertion_pos] + "/verb_chart" + self.driver.current_url[insertion_pos:])
            self.activity_auto = ConjugationAuto(self.driver)

        self.activity_auto.name = name

        self.driver.refresh()
        self.activity_auto.load_data()
        self.driver.back()

    def prepare_start(self):

        self.activity_auto.wrong_questions = int((1 - self.activity_auto.target_percent/100) * self.activity_auto.word_amount)
        print(self.activity_auto.wrong_questions)

        insertion_end = self.driver.current_url.rfind("/")
        insertion_pos = self.driver.current_url.rfind("/", insertion_end) + 1

        self.driver.get(
            self.driver.current_url[:insertion_pos] + "/homework" +
            self.driver.current_url[insertion_end:])

        self.driver.find_element_by_class_name("slider-time").click()
        set_time = self.driver.find_element_by_id("set_time_input")
        set_time.clear()
        set_time.send_keys(self.activity_auto.time_limit)
        self.driver.find_element_by_xpath("//*[contains(text(), 'Save Settings')]").click()
        time.sleep(0.5)
        self.driver.find_element_by_id("start-button").click()

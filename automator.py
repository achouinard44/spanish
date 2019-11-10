import time
import os
from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException,
    ElementClickInterceptedException, ElementNotInteractableException)


class ActivityOptions:
    def __init__(self):
        self.time_limit = None
        self.word_amount = None
        self.target_percent = None
        self.speed = None
        self.auto_submit = None

    def set_options(self, time_limit=None, word_amount=None,
                    target_percent=None, speed=None, auto_submit=None):
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

    def get_elements(self):
        """ overrided by child classes """
        raise NotImplementedError
    
    def get_answer(self, *args, **kwargs):
        """ overrided by child classes """
        raise NotImplementedError

    def try_submit(self):
        try:
            self.driver.find_element_by_xpath(
                "//button[contains(text(), 'Record Score')]").click()
            return True
        except (NoSuchElementException, 
                ElementClickInterceptedException, 
                ElementClickInterceptedException):
            return False

    def check_finished(self):
        try:
            avg = self.driver.find_element_by_xpath(
                    "//label[contains(text(), 'Avg Score')]")
            return avg.is_displayed()
        except NoSuchElementException:
            return False

    def run_automation(self, update_data):
        question_index = 0

        last_action_time = 0.0

        try:
            elements = self.get_elements()
        except NoSuchElementException:
            return False

        start_time = time.time()

        correct_questions = 0

        answering_wrong = False

        while True:
            current_time = time.time()
            elapsed_time = current_time - last_action_time
            try:
                if (question_index < self.word_amount and
                    elapsed_time >= self.speed):

                    last_action_time = time.time()

                    # Checks if percent would be lower than target
                    # if answer is wrong.
                    answering_wrong = (correct_questions / (question_index + 1)
                        > self.target_percent/100.0)
                    if answering_wrong:
                        ans = f"wrong {question_index + 1}"
                    else:
                        ans = self.get_answer(**elements)

                    elements['answer_element'].clear()
                    elements['answer_element'].send_keys(ans)
                    elements['button_element'].click()

                    question_index += 1
                    if not answering_wrong:
                        correct_questions += 1

                time_left = (60 * self.time_limit - int(current_time - start_time))

                if time_left < 0:
                    break

                update_data(time_left % 60,
                            int(time_left / 60),
                            question_index,
                            correct_questions,
                            int(100 * correct_questions / question_index))
                
                time.sleep(0.05)

            except (ElementClickInterceptedException,
                    ElementNotInteractableException):
                continue

        if self.auto_submit:
            while not self.check_finished():
                pass 
            while not self.try_submit():
                pass

        return True


class VocabularyAuto(ActivityAuto):
    def __init__(self, driver):
        ActivityAuto.__init__(self, driver)
        self.vocab_dict = {}
        self.question_element = None

    def get_elements(self):
        elements = {}

        elements['question_element'] = self.driver.find_element_by_id(
            "question-input")
        elements['button_element'] = self.driver.find_element_by_id(
            "check-button")
        elements['answer_element'] = self.driver.find_element_by_id(
            "answer-input")
        
        return elements
    
    def get_answer(self, **kwargs):
        return self.vocab_dict[kwargs['question_element'].text]

    def load_data(self):
        table = self.driver.find_element_by_xpath(
            "//table[@class='table table--fat']")
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

    def get_elements(self):
        elements = {}

        elements['pronoun_element'] = self.driver.find_element_by_id(
                "pronoun-input")
        elements['verb_element'] = self.driver.find_element_by_id(
            "verb-input")
        elements['button_element'] = self.driver.find_element_by_id(
            "check-button")
        elements['answer_element'] = self.driver.find_element_by_id(
            "answer-input")
        
        return elements
    
    def get_answer(self, **kwargs):
        verb = None
        for verb in self.verbs:
            if verb['verb'] == kwargs['verb_element'].text:
                break
        return verb[ConjugationAuto.get_pronoun(
            kwargs['pronoun_element'].text)]

    def load_data(self):
        table_elements = self.driver.find_elements_by_xpath(
            "//div[@class='mb-60 no-break']")
        for elem in table_elements:
            verb = elem.find_element_by_xpath(
                ".//span[@class='fw--bold text--up']").text.lower()
            pronoun_elements = elem.find_elements_by_xpath(
                ".//td[@class='text-center bg-h5']")
            pronouns = [pronoun_element.text
                        for pronoun_element in pronoun_elements]
            conjugated_elements = elem.find_elements_by_xpath(
                ".//td[@class='text-center fsty--italic']")
            conjugated = [
                conjugated_element.text for 
                conjugated_element in conjugated_elements]

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
        self.driver = webdriver.Firefox(
            executable_path=os.getcwd() + "\\res\\geckodriver.exe",
            service_log_path=os.path.devnull)
        self.driver.maximize_window()
        self.driver.get("https://conjuguemos.com/auth/login")

        self.options = None

        self.activity_auto = None

        self.driver.find_element_by_id("identity").send_keys(
            "DO NOT LOGIN HERE! LOGIN IN THE AUTO-CONJUGUEMOS APP")

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

    def login_page(self):
        self.driver.get("https://conjuguemos.com/auth/logout")
        self.driver.get("https://conjuguemos.com/auth/login")

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

        # if looped for entire time (didn't log in or fail log in)
        if self.loop_for_time(5, looped_func):
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
            insertion_pos = self.driver.current_url.find(
                "vocabulary") + len("vocabulary")
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

        insertion_end = self.driver.current_url.rfind("/")
        insertion_pos = self.driver.current_url.rfind("/", insertion_end) + 1

        self.driver.get(
            self.driver.current_url[:insertion_pos] + "/homework" +
            self.driver.current_url[insertion_end:])

        self.driver.find_element_by_class_name("slider-time").click()
        set_time = self.driver.find_element_by_id("set_time_input")
        set_time.clear()
        set_time.send_keys(self.activity_auto.time_limit)
        self.driver.find_element_by_xpath(
            "//*[contains(text(), 'Save Settings')]").click()
        time.sleep(0.5)
        self.driver.find_element_by_id("start-button").click()

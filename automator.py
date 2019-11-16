"""Controls the webdriver for the automation of conjuguemos.

The Automator class navigates through the conjuguemos website. An ActivityAuto
instance in the Automator class specifically loads the data necessary to answer 
the activity questions and runs the loop that automates the activity.
"""

import os
import time

from selenium import webdriver
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        ElementNotInteractableException,
                                        NoSuchElementException)


class Automator:
    """Controls the automation of the webdriver and conjuguemos.

    Attributes:
        driver: The webdriver used to control a browser.
        options: The options that control the conjuguemos activity.
        activity_auto: Automates the conjuguemos activity answers.
    """

    def __init__(self):
        self.driver = webdriver.Firefox(
            executable_path=os.getcwd() + "\\res\\geckodriver.exe",
            service_log_path=os.path.devnull)
        self.driver.maximize_window()
        self.driver.get("https://conjuguemos.com/auth/login")

        self.activity_auto = None
        self.options = None

        self.driver.find_element_by_id("identity").send_keys(
            "DO NOT LOGIN HERE! LOGIN IN THE AUTO-CONJUGUEMOS APP")

    def login_page(self):
        """Returns to the conjuguemos login page."""

        self.driver.get("https://conjuguemos.com/auth/logout")
        self.driver.get("https://conjuguemos.com/auth/login")

    def login(self, username, password):
        """Attempts to login to conjuguemos.
        
        Returns:
            `True` if login is successful, `False` otherwise.
            `"timed out"` if the login timed out.
        """

        username_element = self.driver.find_element_by_id("identity")
        password_element = self.driver.find_element_by_id("password")
        login_element = self.driver.find_element_by_id("login_btn")

        username_element.clear()
        username_element.send_keys(username)
        password_element.clear()
        password_element.send_keys(password)

        login_element.click()

        start = time.time()
        while time.time() - start < 5:
            if self.driver.current_url == "https://conjuguemos.com/auth/login":
                try:
                    self.driver.find_element_by_id("form_errors")
                    self.driver.get(self.driver.current_url)
                    return False
                except NoSuchElementException:
                    pass
            else:
                return True

        return "timed out"

    def get_activities(self):
        """Returns a list of conjuguemos activities."""

        self.driver.implicitly_wait(5)
        activities = self.driver.find_element_by_id("activities")
        activity_element_list = activities.find_elements_by_xpath(".//a")
        self.driver.implicitly_wait(0)

        activity_list = []
        for a in activity_element_list:
            activity_list.append({"name": a.text, "click": a.click})

        return activity_list

    def get_data(self, name):
        """Gets the vocab/conjugation data necessary to automate the activity.

        If the activity is a vocab activity, it creates a VocabularyAuto 
        instance as the activity_auto. If the activity is a conjugation 
        activity, it creates a ConjugationAuto instance as the activity_auto.
        It then loads the necessary data using the activity_auto's load_data
        method.

        Args:
            name: The name of the activity.
        """

        if "vocabulary" in self.driver.current_url:
            insertion_pos = (self.driver.current_url.find("vocabulary")
                + len("vocabulary"))
            new_url = self.driver.current_url[:insertion_pos]
            new_url += "/vocab_chart"+ self.driver.current_url[insertion_pos:]
            self.driver.get(new_url)
            self.activity_auto = VocabularyAuto(self.driver)
        else:
            insertion_pos = self.driver.current_url.find("verb") + len("verb")
            new_url = self.driver.current_url[:insertion_pos]
            new_url += "/verb_chart" + self.driver.current_url[insertion_pos:]
            self.driver.get(new_url)
            self.activity_auto = ConjugationAuto(self.driver)

        self.activity_auto.name = name
        self.options = self.activity_auto.options

        self.driver.refresh()
        self.activity_auto.load_data()
        self.driver.back()

    def prepare_start(self):
        """Sets up and starts the conjugation activity."""

        insertion_end = self.driver.current_url.rfind("/")
        insertion_pos = self.driver.current_url.rfind("/", insertion_end) + 1

        self.driver.get(
            self.driver.current_url[:insertion_pos] + "/homework" +
            self.driver.current_url[insertion_end:])

        self.driver.find_element_by_class_name("slider-time").click()
        set_time = self.driver.find_element_by_id("set_time_input")
        set_time.clear()
        set_time.send_keys(self.activity_auto.options["time_limit"])
        self.driver.find_element_by_xpath(
            "//*[contains(text(), 'Save Settings')]").click()
        time.sleep(0.5)
        self.driver.find_element_by_id("start-button").click()


class ActivityAuto:
    """Parent class for all activity automation classes.

    Controls the automation of the conjuguemos activity, interacting with the
    activity to automatically answer the questions based on an algorithm defined
    by a child class.

    Properties:
        driver: The webdriver used to interact with the browser.
        name: The name of the activity.
        options: The options to be used in the activity automation
    """

    def __init__(self, driver):
        self.driver = driver
        self.name = ""
        self.options = {'time_limit': None,
                        'word_amount': None,
                        'target_percent': None,
                        'speed': None,
                        'auto_submit': None}

    def set_options(self, **kwargs):
        """Sets the activity options."""
        self.options.update(kwargs)

    def get_elements(self):
        """Must be overridden by child class.
        
        This method will get the web elements needed to complete the activity.
        """
        raise NotImplementedError
    
    def get_answer(self, *args, **kwargs):
        """Must be overriden by child class.
        
        This method will get the web elements needed to complete the activity.
        """
        raise NotImplementedError

    def try_submit(self):
        """Tries to submit the activity, returns result.

        Returns:
            `True` if successful, `False` otherwise.
        """

        try:
            self.driver.find_element_by_xpath(
                "//button[contains(text(), 'Record Score')]").click()
            return True
        except (NoSuchElementException, 
                ElementClickInterceptedException, 
                ElementClickInterceptedException):
            return False

    def check_finished(self):
        """Checks if the activity's time is complete."""

        try:
            avg = self.driver.find_element_by_xpath(
                    "//label[contains(text(), 'Avg Score')]")
            return avg.is_displayed()
        except NoSuchElementException:
            return False

    def run_automation(self, update_data):
        """The main loop that automates the conjuguemos activity.

        Uses the child class's methods to answer the activity's questions. Uses
        the ActivityOptions (parent class) to dictate how the activity is
        automated.

        Args:
            update_data: Function that updates the GUI with the current data.

        Returns:
            bool: `True` if activity completed successfully, `False` otherwise.
        """

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
                if (question_index < self.options["word_amount"] and
                    elapsed_time >= self.options["speed"]):

                    last_action_time = time.time()

                    # Checks if percent would be lower than target
                    # if answer is wrong.
                    answering_wrong = (correct_questions / (question_index + 1)
                        > self.options["target_percent"]/100.0)
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

                time_left = (60 * self.options["time_limit"]
                             - int(current_time - start_time))

                if time_left < 0:
                    break

                # Updates the GUI with current automation data
                update_data(time_left % 60,
                            int(time_left / 60),
                            question_index,
                            correct_questions,
                            int(100 * correct_questions / question_index))
                
                time.sleep(0.05)

            except (ElementClickInterceptedException,
                    ElementNotInteractableException):
                continue

        if self.options["auto_submit"]:
            while not self.check_finished():
                pass 
            while not self.try_submit():
                pass

        return True


class VocabularyAuto(ActivityAuto):
    """Activity automator for vocabulary activities.
    
    Attributes:
        vocab_dict: Dictionary of vocab words {english : spanish}.
        question_element: The web element of the question.
    """

    def __init__(self, driver):
        ActivityAuto.__init__(self, driver)
        self.vocab_dict = {}
        self.question_element = None

    def get_elements(self):
        """Gets the necessary web elements to run the automation."""

        elements = {}

        elements['question_element'] = self.driver.find_element_by_id(
            "question-input")
        elements['button_element'] = self.driver.find_element_by_id(
            "check-button")
        elements['answer_element'] = self.driver.find_element_by_id(
            "answer-input")
        
        return elements
    
    def get_answer(self, **kwargs):
        """Gets the correct answer based on the activity question."""

        return self.vocab_dict[kwargs['question_element'].text]

    def load_data(self):
        """Parses and saves the data from the vocabulary chart

        The current site must be the conjuguemos vocabulary chart for the
        current activity.
        """

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
    """Activity automator for conjugation activities.

    Attributes:
        verbs: list of verb dictionaries in the form {pronoun : conjugation}.
        pronoun_element: Web element of the pronoun part of the question.
        verb_element: Web element of the verb part of the question.
    """
    def __init__(self, driver):
        ActivityAuto.__init__(self, driver)
        self.verbs = []
        self.pronoun_element = None
        self.verb_element = None

    def get_elements(self):
        """Gets the necessary elements to run the automation."""

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
        """Gets the correct answer based on question data."""

        verb = None
        for verb in self.verbs:
            if verb['verb'] == kwargs['verb_element'].text:
                break
        return verb[ConjugationAuto.get_pronoun(
            kwargs['pronoun_element'].text)]

    def load_data(self):
        """Parses and saves the data from the verb charts

        The current site must be the conjuguemos verb charts for the
        current activity.
        """

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
        """Gets the pronoun associated with a noun."""

        noun = noun.lower()
        if noun in ['yo', 'tú', 'él', 'ella', 'usted', 'nosotros', 
                    'vosotros', 'ellos', 'ellas', 'ustedes']:
            return noun
        elif " y " in noun:
            if " yo" in noun or "yo " in noun:
                return "nosotros"
            else:
                return "ellos"
        else:
            return "él"

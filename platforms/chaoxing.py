"""
超星学习通平台模块
处理超星学习通的登录检测、课程列表、题目提取、答案填写等
"""

import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class ChaoxingPlatform:
    """超星学习通平台适配器"""

    def __init__(self):
        self.login_url = "https://passport2.chaoxing.com/login"
        self.base_url = "https://mooc1.chaoxing.com"
        self.current_tab_handle = None

    def wait_for_login(self, driver):
        print("等待登录完成...")
        max_wait = 120
        for i in range(max_wait):
            time.sleep(1)
            try:
                current_url = driver.current_url
                if "passport2.chaoxing.com" not in current_url:
                    print("✅ 登录成功！")
                    return True
                elements = driver.find_elements(By.CSS_SELECTOR, ".head_portrait, .user-info, #headPic")
                if elements:
                    print("✅ 登录成功！")
                    return True
            except Exception:
                continue
        print("⏰ 等待登录超时，请重试。")
        return False

    def get_course_list(self, driver):
        courses = []
        try:
            driver.get("https://mooc1.chaoxing.com/mycourse/studentcourse")
            time.sleep(3)
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".course-list .course-item, .clearfix.course"))
                )
            except TimeoutException:
                pass
            course_elements = driver.find_elements(
                By.CSS_SELECTOR,
                ".course-list .course-item, .clearfix.course, ul.course-list li"
            )
            for elem in course_elements:
                try:
                    name_elem = elem.find_element(By.CSS_SELECTOR, ".course-name, h3 a, .title")
                    name = name_elem.text.strip()
                    link_elem = elem.find_element(By.CSS_SELECTOR, "a[href*='course']")
                    url = link_elem.get_attribute("href")
                    if name and url:
                        courses.append({"name": name, "url": url, "id": url})
                except NoSuchElementException:
                    continue
            if not courses:
                driver.get("https://mooc1-2.chaoxing.com/mycourse/studentcourse")
                time.sleep(3)
                course_elements = driver.find_elements(By.CSS_SELECTOR, "#courseList .course, .course-item")
                for elem in course_elements:
                    try:
                        name = elem.text.strip().split("\n")[0]
                        link = elem.find_element(By.TAG_NAME, "a")
                        url = link.get_attribute("href")
                        if name and url:
                            courses.append({"name": name, "url": url, "id": url})
                    except NoSuchElementException:
                        continue
        except Exception as e:
            print(f"获取课程列表出错：{e}")
        return courses

    def get_task_list(self, driver, course, task_type="quiz"):
        tasks = []
        try:
            driver.get(course["url"])
            time.sleep(3)
            if task_type == "quiz":
                try:
                    homework_tab = driver.find_element(By.CSS_SELECTOR, "a[href*='homework'], .tab-item:contains('作业'), span:contains('作业')")
                    homework_tab.click()
                    time.sleep(2)
                except NoSuchElementException:
                    course_id = self._extract_course_id(course["url"])
                    driver.get(f"https://mooc1.chaoxing.com/mooc2/work/list?courseId={course_id}")
                    time.sleep(3)
            else:
                try:
                    exam_tab = driver.find_element(By.CSS_SELECTOR, "a[href*='exam'], .tab-item:contains('考试')")
                    exam_tab.click()
                    time.sleep(2)
                except NoSuchElementException:
                    course_id = self._extract_course_id(course["url"])
                    driver.get(f"https://mooc1.chaoxing.com/mooc2/exam/list?courseId={course_id}")
                    time.sleep(3)
            task_elements = driver.find_elements(By.CSS_SELECTOR, ".work-list li, .job-item, .clearfix.jobList, table tbody tr")
            for elem in task_elements:
                try:
                    name_elem = elem.find_element(By.CSS_SELECTOR, ".job-name a, .work-name, td:nth-child(2) a, .title")
                    name = name_elem.text.strip()
                    url = name_elem.get_attribute("href")
                    status_elem = elem.find_element(By.CSS_SELECTOR, ".job-status, .status, td:last-child")
                    status_text = status_elem.text.strip()
                    completed = "已批" in status_text or "100" in status_text or "已完成" in status_text
                    if name:
                        tasks.append({"name": name, "url": url, "completed": completed})
                except NoSuchElementException:
                    continue
        except Exception as e:
            print(f"获取任务列表出错：{e}")
        return tasks

    def enter_task(self, driver, task):
        if task.get("url"):
            driver.get(task["url"])
            time.sleep(3)
        else:
            print("任务没有URL，无法进入")

    def extract_questions(self, driver):
        questions = []
        try:
            time.sleep(2)
            question_elements = driver.find_elements(By.CSS_SELECTOR, ".TiMu, .question, .exam-question, .topic-item")
            if not question_elements:
                question_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='question'], div[class*='topic'], .clearfix.answerBg")
            for i, elem in enumerate(question_elements):
                try:
                    question = self._parse_question(elem, i)
                    if question:
                        questions.append(question)
                except Exception as e:
                    print(f"  ⚠️ 解析第 {i + 1} 题出错：{e}")
                    continue
            if not questions:
                questions = self._extract_from_iframe(driver)
        except Exception as e:
            print(f"提取题目出错：{e}")
        return questions

    def _parse_question(self, element, index):
        question = {"index": index, "type": "", "text": "", "options": [], "element": element}
        try:
            type_elem = element.find_element(By.CSS_SELECTOR, ".Zy_TItle, .question-type, .type, span:first-child")
            type_text = type_elem.text.strip()
            question["type"] = self._parse_question_type(type_text)
            text_elem = element.find_element(By.CSS_SELECTOR, ".Zy_TItle, .question-content, .stem, .title_text")
            question["text"] = text_elem.text.strip()
            if question["type"] in question["text"]:
                question["text"] = question["text"].replace(question["type"], "").strip()
                question["text"] = re.sub(r'^[\d]+[、.．]\s*', '', question["text"])
            if question["type"] in ("单选", "多选", "判断"):
                option_elements = element.find_elements(By.CSS_SELECTOR, ".Zy_ulTop li, .option-item, ul.ul_top li, .answerBg li")
                for opt_elem in option_elements:
                    opt_text = opt_elem.text.strip()
                    if opt_text:
                        question["options"].append(opt_text)
                if question["type"] == "判断" and not question["options"]:
                    question["options"] = ["正确", "错误"]
        except NoSuchElementException:
            full_text = element.text.strip()
            if full_text:
                question["text"] = full_text
                question["type"] = self._guess_question_type(full_text)
        return question if question["text"] else None

    def _parse_question_type(self, type_text):
        type_text = type_text.upper()
        if "单选" in type_text or "SINGLE" in type_text:
            return "单选"
        elif "多选" in type_text or "MULTIPLE" in type_text:
            return "多选"
        elif "判断" in type_text or "JUDGE" in type_text:
            return "判断"
        elif "填空" in type_text or "FILL" in type_text:
            return "填空"
        elif "简答" in type_text or "问答" in type_text or "论述" in type_text:
            return "简答"
        return "未知"

    def _guess_question_type(self, text):
        if "A." in text or "B." in text:
            return "单选"
        if "正确" in text and "错误" in text:
            return "判断"
        if "___" in text or "____" in text:
            return "填空"
        return "简答"

    def _extract_from_iframe(self, driver):
        questions = []
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    driver.switch_to.frame(iframe)
                    time.sleep(1)
                    questions = self.extract_questions(driver)
                    if questions:
                        break
                    driver.switch_to.default_content()
                except Exception:
                    driver.switch_to.default_content()
                    continue
        except Exception:
            pass
        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
        return questions

    def fill_answer(self, driver, question, answer):
        try:
            element = question["element"]
            q_type = question["type"]
            if q_type in ("单选", "多选"):
                self._fill_choice_answer(element, answer, q_type)
            elif q_type == "判断":
                self._fill_judge_answer(element, answer)
            elif q_type == "填空":
                self._fill_blank_answer(element, answer)
            elif q_type == "简答":
                self._fill_essay_answer(element, answer)
            else:
                print(f"  ⚠️ 不支持的题型：{q_type}")
            time.sleep(0.5)
        except Exception as e:
            print(f"  ⚠️ 填写答案出错：{e}")

    def _fill_choice_answer(self, element, answer, q_type):
        options = element.find_elements(By.CSS_SELECTOR, ".Zy_ulTop li, .option-item, ul.ul_top li, .answerBg li")
        for opt in options:
            opt_text = opt.text.strip()
            if answer in opt_text or opt_text in answer:
                try:
                    radio = opt.find_element(By.CSS_SELECTOR, "input[type='radio'], input[type='checkbox']")
                    if not radio.is_selected():
                        radio.click()
                    return
                except NoSuchElementException:
                    try:
                        opt.click()
                        return
                    except Exception:
                        pass
        letter_map = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}
        for letter, idx in letter_map.items():
            if letter in answer and idx < len(options):
                try:
                    options[idx].click()
                    return
                except Exception:
                    pass

    def _fill_judge_answer(self, element, answer):
        options = element.find_elements(By.CSS_SELECTOR, ".Zy_ulTop li, .option-item, ul.ul_top li")
        is_correct = "正确" in answer or "对" in answer
        for opt in options:
            opt_text = opt.text.strip()
            if (is_correct and ("正确" in opt_text or "对" in opt_text)) or \
               (not is_correct and ("错误" in opt_text or "错" in opt_text)):
                try:
                    opt.click()
                    return
                except Exception:
                    pass
        if options:
            try:
                options[0 if is_correct else 1].click()
            except Exception:
                pass

    def _fill_blank_answer(self, element, answer):
        try:
            input_elem = element.find_element(By.CSS_SELECTOR, "input[type='text'], .blank-input, textarea, input")
            input_elem.clear()
            input_elem.send_keys(answer)
        except NoSuchElementException:
            pass

    def _fill_essay_answer(self, element, answer):
        try:
            textarea = element.find_element(By.CSS_SELECTOR, "textarea, .answer-textarea, input[type='text']")
            textarea.clear()
            textarea.send_keys(answer)
        except NoSuchElementException:
            print("  ⚠️ 未找到输入框")

    def submit(self, driver):
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, ".zy_btn, .btn-submit, input[type='submit'], button:contains('提交'), .submitBtn")
            submit_btn.click()
            time.sleep(1)
            try:
                confirm_btn = driver.find_element(By.CSS_SELECTOR, ".layui-layer-btn0, .btn-confirm, button:contains('确定')")
                confirm_btn.click()
            except NoSuchElementException:
                pass
            time.sleep(2)
        except Exception as e:
            print(f"提交出错：{e}")

    def back_to_task_list(self, driver):
        try:
            driver.back()
            time.sleep(2)
        except Exception:
            pass

    def _extract_course_id(self, url):
        match = re.search(r'courseId=(\d+)', url)
        if match:
            return match.group(1)
        match = re.search(r'/(\d+)\.html', url)
        if match:
            return match.group(1)
        return ""

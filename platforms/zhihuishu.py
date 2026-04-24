"""
智慧树（知到）平台模块
处理智慧树的登录检测、课程列表、题目提取、答案填写等
"""

import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class ZhihuishuPlatform:
    """智慧树（知到）平台适配器"""

    def __init__(self):
        self.login_url = "https://www.zhihuishu.com/"
        self.base_url = "https://www.zhihuishu.com"

    def wait_for_login(self, driver):
        print("等待登录完成...")
        max_wait = 120
        for i in range(max_wait):
            time.sleep(1)
            try:
                current_url = driver.current_url
                if "login" not in current_url.lower() or "passport" not in current_url.lower():
                    elements = driver.find_elements(By.CSS_SELECTOR, ".user-name, .header-user, .avatar, #user-name")
                    if elements:
                        print("✅ 登录成功！")
                        return True
                    if "zhihuishu.com" in current_url and "login" not in current_url.lower():
                        print("✅ 登录成功！")
                        return True
            except Exception:
                continue
        print("⏰ 等待登录超时，请重试。")
        return False

    def get_course_list(self, driver):
        courses = []
        try:
            driver.get("https://www.zhihuishu.com/portal")
            time.sleep(3)
            try:
                my_course_btn = driver.find_element(By.CSS_SELECTOR, "a[href*='course'], .nav-item:contains('我的课程'), span:contains('我的课程')")
                my_course_btn.click()
                time.sleep(2)
            except NoSuchElementException:
                pass
            driver.get("https://www.zhihuishu.com/portal/mycourse")
            time.sleep(3)
            course_elements = driver.find_elements(By.CSS_SELECTOR, ".course-list .course-item, .course-card, .list-item, .course-item-wrap")
            for elem in course_elements:
                try:
                    name_elem = elem.find_element(By.CSS_SELECTOR, ".course-name, .title, h3, .name")
                    name = name_elem.text.strip()
                    link_elem = elem.find_element(By.TAG_NAME, "a")
                    url = link_elem.get_attribute("href")
                    if name and url:
                        courses.append({"name": name, "url": url, "id": url})
                except NoSuchElementException:
                    continue
            if not courses:
                links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/course/'], a[href*='learn']")
                for link in links:
                    try:
                        name = link.text.strip()
                        url = link.get_attribute("href")
                        if name and url and len(name) > 2:
                            courses.append({"name": name, "url": url, "id": url})
                    except Exception:
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
                nav_items = driver.find_elements(By.CSS_SELECTOR, ".chapter-item, .nav-list li, .menu-item")
                for item in nav_items:
                    try:
                        text = item.text.strip()
                        if any(kw in text for kw in ["作业", "章测试", "练习", "测验"]):
                            item.click()
                            time.sleep(2)
                            break
                    except Exception:
                        continue
            else:
                nav_items = driver.find_elements(By.CSS_SELECTOR, ".chapter-item, .nav-list li, .menu-item")
                for item in nav_items:
                    try:
                        text = item.text.strip()
                        if "考试" in text:
                            item.click()
                            time.sleep(2)
                            break
                    except Exception:
                        continue
            task_elements = driver.find_elements(By.CSS_SELECTOR, ".exam-item, .work-item, .list-item, .task-item, .test-item")
            for elem in task_elements:
                try:
                    name_elem = elem.find_element(By.CSS_SELECTOR, ".exam-name, .work-name, .title, .name, a")
                    name = name_elem.text.strip()
                    url = name_elem.get_attribute("href")
                    status_elem = elem.find_element(By.CSS_SELECTOR, ".status, .exam-status, .state")
                    status_text = status_elem.text.strip()
                    completed = any(kw in status_text for kw in ["已完成", "已批", "100", "通过"])
                    if name:
                        tasks.append({"name": name, "url": url, "completed": completed})
                except NoSuchElementException:
                    continue
        except Exception as e:
            print(f"获取任务列表出错：{e}")
        return tasks

    def enter_task(self, driver, task):
        if task.get("url"):
            current_handles = driver.window_handles
            driver.get(task["url"])
            time.sleep(3)
            new_handles = driver.window_handles
            if len(new_handles) > len(current_handles):
                driver.switch_to.window(new_handles[-1])
        else:
            print("任务没有URL，无法进入")

    def extract_questions(self, driver):
        questions = []
        try:
            time.sleep(2)
            question_elements = driver.find_elements(By.CSS_SELECTOR, ".exam-question, .question-item, .topic-item, .el-form-item, .questionBox")
            if not question_elements:
                question_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='question'], div[class*='topic'], .test-question")
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
            type_elem = element.find_element(By.CSS_SELECTOR, ".question-type, .type-label, .topic-type, .num-type")
            type_text = type_elem.text.strip()
            question["type"] = self._parse_question_type(type_text)
            text_elem = element.find_element(By.CSS_SELECTOR, ".question-content, .stem, .topic-content, .question-stem, .title")
            question["text"] = text_elem.text.strip()
            if question["type"] and question["type"] in question["text"]:
                question["text"] = question["text"].replace(question["type"], "").strip()
                question["text"] = re.sub(r'^[\d]+[、.．]\s*', '', question["text"])
            if question["type"] in ("单选", "多选", "判断"):
                option_elements = element.find_elements(By.CSS_SELECTOR, ".option-item, .el-radio, .el-checkbox, ul.options li, .answer-option")
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
        if "单选" in type_text:
            return "单选"
        elif "多选" in type_text:
            return "多选"
        elif "判断" in type_text:
            return "判断"
        elif "填空" in type_text:
            return "填空"
        elif "简答" in type_text or "问答" in type_text:
            return "简答"
        return "未知"

    def _guess_question_type(self, text):
        if "A." in text or "B." in text:
            return "单选"
        if "正确" in text and "错误" in text:
            return "判断"
        if "___" in text:
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
        options = element.find_elements(By.CSS_SELECTOR, ".option-item, .el-radio, .el-checkbox, .answer-option, li.option")
        for opt in options:
            opt_text = opt.text.strip()
            if answer in opt_text or opt_text in answer:
                try:
                    radio = opt.find_element(By.CSS_SELECTOR, "input[type='radio'], input[type='checkbox'], .el-radio__input, .el-checkbox__input")
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
        options = element.find_elements(By.CSS_SELECTOR, ".option-item, .el-radio, li.option")
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
            input_elem = element.find_element(By.CSS_SELECTOR, "input[type='text'], .el-input__inner, textarea")
            input_elem.clear()
            input_elem.send_keys(answer)
        except NoSuchElementException:
            print("  ⚠️ 未找到填空输入框")

    def _fill_essay_answer(self, element, answer):
        try:
            textarea = element.find_element(By.CSS_SELECTOR, "textarea, .el-textarea__inner, .answer-input")
            textarea.clear()
            textarea.send_keys(answer)
        except NoSuchElementException:
            print("  ⚠️ 未找到简答输入框")

    def submit(self, driver):
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, ".submit-btn, .btn-submit, button:contains('提交'), .el-button--primary")
            submit_btn.click()
            time.sleep(1)
            try:
                confirm_btn = driver.find_element(By.CSS_SELECTOR, ".el-message-box__btns .el-button--primary, .btn-confirm, button:contains('确定')")
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

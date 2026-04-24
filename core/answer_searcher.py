"""
答案搜索模块
通过多个题库网站联网搜索题目答案
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote


class AnswerSearcher:
    """答案搜索器 - 多源搜索"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        self.sources = [
            self._search_tiku,
            self._search_baidu,
            self._search_bing,
        ]

    def search(self, question_text, question_type="", options=None):
        clean_question = self._clean_question(question_text)
        if not clean_question:
            return None
        print(f"  🔍 搜索中：{clean_question[:40]}...")
        keyword = self._build_keyword(clean_question, question_type, options)
        for search_func in self.sources:
            try:
                answer = search_func(keyword, clean_question, question_type, options)
                if answer:
                    return answer
            except Exception as e:
                print(f"  ⚠️ 搜索源出错：{e}")
                continue
        return None

    def _clean_question(self, text):
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'[\r\n\t]', ' ', text)
        text = re.sub(r'^[\d一二三四五六七八九十]+[、.．)）]\s*', '', text)
        return text

    def _build_keyword(self, question, question_type, options):
        keyword = question
        if options and question_type in ("单选", "多选"):
            opts_text = " ".join(str(o) for o in options if o)
            keyword = f"{question} {opts_text}"
        return keyword

    def _search_tiku(self, keyword, question, q_type, options):
        apis = [self._search_via_gowk, self._search_via_yanxi]
        for api_func in apis:
            try:
                answer = api_func(keyword, question, q_type, options)
                if answer:
                    return answer
            except Exception:
                continue
        return None

    def _search_via_gowk(self, keyword, question, q_type, options):
        url = f"https://www.gowk.net/cx/search?keyword={quote(keyword)}"
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                results = soup.select(".search-result, .answer, .result-item")
                for result in results:
                    text = result.get_text(strip=True)
                    if text and len(text) > 2:
                        return self._format_answer(text, q_type, options)
        except Exception:
            pass
        return None

    def _search_via_yanxi(self, keyword, question, q_type, options):
        url = f"https://app.yanxishe.com/api/v1/search?q={quote(keyword)}"
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list):
                    for item in data[:3]:
                        answer_text = item.get("answer", "")
                        if answer_text:
                            return self._format_answer(answer_text, q_type, options)
        except Exception:
            pass
        return None

    def _search_baidu(self, keyword, question, q_type, options):
        url = f"https://www.baidu.com/s?wd={quote(keyword + ' 答案')}"
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                results = soup.select(".c-abstract, .result .c-span-last")
                for result in results:
                    text = result.get_text(strip=True)
                    answer = self._extract_answer_from_text(text, q_type, options)
                    if answer:
                        return answer
        except Exception:
            pass
        return None

    def _search_bing(self, keyword, question, q_type, options):
        url = f"https://cn.bing.com/search?q={quote(keyword + ' 答案 题库')}"
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                results = soup.select(".b_caption p, .b_algo p")
                for result in results:
                    text = result.get_text(strip=True)
                    answer = self._extract_answer_from_text(text, q_type, options)
                    if answer:
                        return answer
        except Exception:
            pass
        return None

    def _extract_answer_from_text(self, text, q_type, options):
        if not text or len(text) < 2:
            return None
        if q_type == "判断":
            if "正确" in text or "对" in text or "√" in text or "true" in text.lower():
                return "正确"
            if "错误" in text or "错" in text or "×" in text or "false" in text.lower():
                return "错误"
        if q_type in ("单选", "多选") and options:
            for opt in options:
                opt_str = str(opt)
                if opt_str and opt_str in text:
                    return opt_str
        answer_match = re.search(r'(?:答案|正确答案|参考答案)[：:]\s*(.+?)(?:\n|$|。)', text)
        if answer_match:
            return answer_match.group(1).strip()
        if len(text) > 10 and any(kw in text for kw in ["正确", "答案", "选", "A.", "B.", "C.", "D."]):
            return text[:200]
        return None

    def _format_answer(self, answer_text, q_type, options):
        if not answer_text:
            return None
        answer_text = answer_text.strip()
        if q_type == "判断":
            if any(kw in answer_text for kw in ["正确", "对", "√", "true", "T"]):
                return "正确"
            if any(kw in answer_text for kw in ["错误", "错", "×", "false", "F"]):
                return "错误"
        if q_type in ("单选", "多选") and options:
            for i, opt in enumerate(options):
                opt_str = str(opt).strip()
                if opt_str and opt_str in answer_text:
                    return opt_str
            letters = re.findall(r'[A-D]', answer_text)
            if letters:
                return letters[0]
        return answer_text[:500] if len(answer_text) > 500 else answer_text

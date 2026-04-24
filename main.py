# 网课自动化答题工具
# 自动完成超星学习通和智慧树（知到）的练习题和考试题

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.browser import BrowserManager
from core.answer_searcher import AnswerSearcher
from platforms.chaoxing import ChaoxingPlatform
from platforms.zhihuishu import ZhihuishuPlatform


def main():
    print("=" * 60)
    print("       网课自动化答题工具 v1.0")
    print("       支持平台：超星学习通 / 智慧树（知到）")
    print("=" * 60)

    print("\n请选择网课平台：")
    print("  1. 超星学习通")
    print("  2. 智慧树（知到）")
    choice = input("\n请输入编号 (1/2): ").strip()

    if choice == "1":
        platform = ChaoxingPlatform()
        platform_name = "超星学习通"
    elif choice == "2":
        platform = ZhihuishuPlatform()
        platform_name = "智慧树（知到）"
    else:
        print("无效选择，退出。")
        return

    print(f"\n已选择：{platform_name}")

    print("\n请选择任务类型：")
    print("  1. 练习题")
    print("  2. 考试题")
    task_choice = input("\n请输入编号 (1/2): ").strip()
    task_type = "quiz" if task_choice == "1" else "exam"

    print("\n请选择浏览器：")
    print("  1. Google Chrome（默认）")
    print("  2. Microsoft Edge")
    browser_choice = input("\n请输入编号 (1/2，直接回车默认Chrome): ").strip()
    browser_type = "edge" if browser_choice == "2" else "chrome"
    browser_name = "Microsoft Edge" if browser_type == "edge" else "Google Chrome"

    print(f"\n正在启动 {browser_name}...")
    browser = BrowserManager(headless=False, browser_type=browser_type)
    driver = browser.get_driver()
    searcher = AnswerSearcher()

    try:
        print(f"\n正在打开 {platform_name} 登录页面...")
        print("⚠️  请在浏览器中手动完成登录（扫码或输入密码）")
        print("⚠️  登录完成后，脚本会自动继续...")
        driver.get(platform.login_url)

        platform.wait_for_login(driver)
        print("\n✅ 检测到登录成功！")

        print("\n正在获取课程列表...")
        courses = platform.get_course_list(driver)

        if not courses:
            print("未找到课程，请确认已登录且已选课。")
            return

        print("\n可用课程：")
        for i, course in enumerate(courses):
            print(f"  {i + 1}. {course['name']}")

        course_choice = input("\n请输入课程编号: ").strip()
        try:
            course_idx = int(course_choice) - 1
            selected_course = courses[course_idx]
        except (ValueError, IndexError):
            print("无效选择，退出。")
            return

        print(f"\n已选择课程：{selected_course['name']}")

        print("\n正在获取任务列表...")
        tasks = platform.get_task_list(driver, selected_course, task_type)

        if not tasks:
            print("未找到可用的任务。")
            return

        print("\n可用任务：")
        for i, task in enumerate(tasks):
            status = "✅已完成" if task.get("completed") else "⏳待完成"
            print(f"  {i + 1}. {task['name']} [{status}]")

        task_num = input("\n请输入任务编号（多个用逗号分隔，如 1,3,5，输入 all 做全部）: ").strip()

        if task_num.lower() == "all":
            selected_tasks = [t for t in tasks if not t.get("completed")]
        else:
            indices = [int(x.strip()) - 1 for x in task_num.split(",")]
            selected_tasks = [tasks[i] for i in indices if i < len(tasks)]

        if not selected_tasks:
            print("没有需要做的任务。")
            return

        for task in selected_tasks:
            print(f"\n{'=' * 60}")
            print(f"正在处理：{task['name']}")
            print(f"{'=' * 60}")

            platform.enter_task(driver, task)

            print("\n正在提取题目...")
            questions = platform.extract_questions(driver)

            if not questions:
                print("未提取到题目，可能该任务已完成或页面结构变化。")
                continue

            print(f"共提取到 {len(questions)} 道题目")

            correct_count = 0
            for i, q in enumerate(questions):
                print(f"\n[{i + 1}/{len(questions)}] {q['type']}: {q['text'][:50]}...")
                answer = searcher.search(q["text"], q["type"], q.get("options"))
                if answer:
                    print(f"  📝 找到答案：{answer}")
                    platform.fill_answer(driver, q, answer)
                    correct_count += 1
                else:
                    print(f"  ❌ 未找到答案，跳过")

            print(f"\n答题完成！已填写 {correct_count}/{len(questions)} 题")
            submit = input("是否提交？(y/n): ").strip().lower()
            if submit == "y":
                platform.submit(driver)
                print("✅ 已提交！")
            else:
                print("⏸️ 未提交，请手动检查后提交。")

            platform.back_to_task_list(driver)

        print("\n🎉 全部任务处理完成！")

    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断，正在退出...")
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\n按回车键关闭浏览器...")
        browser.close()


if __name__ == "__main__":
    main()

"""
Playwright 脚本编辑弹窗

通过 node.json registrations 字段注册到引擎的 Editor 扩展点。
"""
import ast

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMenu,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from .utils import (
    build_playwright_config_schema,
    extract_playwright_params,
)


# 预设模板
_TEMPLATES = {
    "浏览器截图": (
        "from playwright.sync_api import sync_playwright\n"
        "\n"
        "with sync_playwright() as p:\n"
        "    browser = p.chromium.launch(headless=LF_HEADLESS)\n"
        "    page = browser.new_page()\n"
        "    page.goto('{{url}}')\n"
        "    page.screenshot(path='screenshot.png')\n"
        "    lf_add_artifact('screenshot', 'screenshot.png')\n"
        "    lf_set_output({'screenshot_path': 'screenshot.png'})\n"
    ),
    "下载文件": (
        "from playwright.sync_api import sync_playwright\n"
        "\n"
        "with sync_playwright() as p:\n"
        "    browser = p.chromium.launch(headless=LF_HEADLESS)\n"
        "    page = browser.new_page()\n"
        "    page.goto('{{url}}')\n"
        "    # 点击触发下载的链接/按钮\n"
        "    page.get_by_role('link').click()\n"
        "    # 下载由系统自动保存到下载目录\n"
        "    lf_set_output({'url': '{{url}}'})\n"
    ),
    "下载并读取": (
        "from playwright.sync_api import sync_playwright\n"
        "\n"
        "with sync_playwright() as p:\n"
        "    browser = p.chromium.launch(headless=LF_HEADLESS)\n"
        "    page = browser.new_page()\n"
        "    page.goto('{{url}}')\n"
        "    # 点击触发下载\n"
        "    page.get_by_role('link').click()\n"
        "    # 等待下载完成（若已启用自动下载则无需手动调用）\n"
        "    lf_download_wait()\n"
        "    # 读取下载的文件\n"
        "    import os\n"
        "    files = os.listdir(LF_DOWNLOAD_DIR)\n"
        "    lf_set_output({'files': files, 'url': '{{url}}'})\n"
    ),
    "多页面抓取": (
        "from playwright.sync_api import sync_playwright\n"
        "\n"
        "with sync_playwright() as p:\n"
        "    browser = p.chromium.launch(headless=LF_HEADLESS)\n"
        "    page = browser.new_page()\n"
        "    results = []\n"
        "    for url in {{urls}}:\n"
        "        page.goto(url)\n"
        "        title = page.title()\n"
        "        results.append({'url': url, 'title': title})\n"
        "    lf_set_output({'results': results})\n"
    ),
    "表单填写": (
        "from playwright.sync_api import sync_playwright\n"
        "\n"
        "with sync_playwright() as p:\n"
        "    browser = p.chromium.launch(headless=LF_HEADLESS)\n"
        "    page = browser.new_page()\n"
        "    page.goto('{{url}}')\n"
        "    page.fill('#username', '{{username}}')\n"
        "    page.fill('#password', '{{password}}')\n"
        "    page.click('button[type=submit]')\n"
        "    page.wait_for_load_state('networkidle')\n"
        "    lf_set_output({'result_url': page.url})\n"
    ),
}

# 帮助函数列表
_HELP_FUNCTIONS = [
    ("lf_set_output(data=None, **kwargs)", "设置结构化输出数据"),
    ("lf_download_wait(timeout=None, min_stable_seconds=2)", "等待下载目录中的文件稳定"),
    ("lf_read_file(file_path, encoding='utf-8', max_size_mb=10)", "读取文件内容"),
    ("lf_add_artifact(name, path)", "注册产物路径"),
    ("lf_create_context(browser, **kwargs)", "创建浏览器上下文（自动 accept_downloads）"),
    ("lf_log(message)", "输出日志（子进程实时刷新）"),
    ("LF_HEADLESS (bool)", "无头模式配置值"),
    ("LF_DOWNLOAD_DIR (str)", "下载目录路径"),
    ("LF_ARTIFACTS_DIR (str)", "产物目录路径"),
    ("LF_TIMEOUT_SECONDS (int)", "超时时间"),
    ("LF_INPUT_DATA (dict)", "上游输入数据"),
    ("LF_PARAMS (dict)", "参数占位符运行时值"),
]


class PlaywrightScriptDialog(QDialog):
    """Playwright Python 脚本编辑器"""

    def __init__(
        self,
        script_source: str = "",
        existing_param_schema: dict | None = None,
        node_name: str = "Playwright",
        parent=None,
    ):
        super().__init__(parent)
        self._existing_param_schema = existing_param_schema or {}
        self._result_script = script_source or ""
        self._result_param_schema = build_playwright_config_schema(
            extract_playwright_params(self._result_script),
            self._existing_param_schema,
        )
        self.setWindowTitle(f"编辑 Playwright 脚本 - {node_name}")
        self.setMinimumSize(900, 620)
        self._setup_ui()
        self._apply_style()
        self.editor.setPlainText(self._result_script)
        self._refresh_preview()

    def _insert_template(self, template_name: str):
        code = _TEMPLATES.get(template_name)
        if not code:
            return
        cursor = self.editor.textCursor()
        cursor.insertText(code)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()
        self._refresh_preview()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        template_btn = QPushButton("📖 插入模板")
        template_menu = QMenu(self)
        for name in _TEMPLATES:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, n=name: self._insert_template(n))
            template_menu.addAction(action)
        template_btn.setMenu(template_menu)
        toolbar.addWidget(template_btn)

        help_btn = QPushButton("❓ 帮助函数")
        help_menu = QMenu(self)
        for sig, desc in _HELP_FUNCTIONS:
            action = QAction(sig, self)
            action.setToolTip(desc)
            help_menu.addAction(action)
        help_btn.setMenu(help_menu)
        toolbar.addWidget(help_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        help_label = QLabel(
            "粘贴 Python Playwright 脚本。可使用 {{report_date}} 这类占位符，保存后会自动生成参数。\n"
            "提示：下载文件时，系统会自动保存到下载目录并读取内容，无需手动处理下载事件。"
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        content = QHBoxLayout()
        content.setSpacing(12)

        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(QLabel("脚本代码"))

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(
            "例如:\n"
            "from playwright.sync_api import sync_playwright\n\n"
            "with sync_playwright() as p:\n"
            "    browser = p.chromium.launch(headless=LF_HEADLESS)\n"
            "    page = browser.new_page()\n"
            "    page.goto('https://example.com')\n\n"
            "    # 触发下载（系统自动保存到下载目录）\n"
            "    page.get_by_role('link').click()\n\n"
            "    lf_set_output({'date': '{{report_date}}'})\n"
        )
        font = QFont("Consolas", 10)
        self.editor.setFont(font)
        editor_layout.addWidget(self.editor)

        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)
        editor_layout.addWidget(self.validation_label)

        content.addWidget(editor_container, 3)

        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(QLabel("参数预览"))

        self.param_list = QListWidget()
        preview_layout.addWidget(self.param_list)
        preview_hint = QLabel("仅展示脚本中识别出的 {{param}} 业务参数。")
        preview_hint.setWordWrap(True)
        preview_layout.addWidget(preview_hint)

        content.addWidget(preview_container, 1)
        layout.addLayout(content)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        validate_btn = QPushButton("校验并预览")
        validate_btn.clicked.connect(self._on_validate)
        button_layout.addWidget(validate_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _apply_style(self):
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: palette(window);
            }}
            QPlainTextEdit {{
                font-family: Consolas;
                font-size: 10pt;
            }}
            """
        )

    def _validate_source(self, source_code: str):
        if not source_code.strip():
            raise ValueError("请输入 Playwright Python 脚本")
        try:
            ast.parse(source_code)
        except SyntaxError as exc:
            raise ValueError(f"语法错误: {exc.msg} (第{exc.lineno}行)") from exc

    def _refresh_preview(self):
        source_code = self.editor.toPlainText()
        param_names = extract_playwright_params(source_code)
        self.param_list.clear()
        if param_names:
            self.param_list.addItems(param_names)
        else:
            self.param_list.addItem("未识别到业务参数")
        self._result_script = source_code
        self._result_param_schema = build_playwright_config_schema(
            param_names,
            self._existing_param_schema,
        )
        return param_names

    def _on_validate(self):
        try:
            self._validate_source(self.editor.toPlainText())
            param_names = self._refresh_preview()
            self.validation_label.setText(
                f"校验通过，识别到 {len(param_names)} 个业务参数。"
            )
        except Exception as exc:
            self.validation_label.setText(str(exc))

    def _on_save(self):
        try:
            self._validate_source(self.editor.toPlainText())
            self._refresh_preview()
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "脚本校验失败", str(exc))

    def get_result(self):
        return {
            "script_source": self._result_script,
            "param_schema": self._result_param_schema,
            "param_names": extract_playwright_params(self._result_script),
        }
